import datetime
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.app.models.schema import (
    get_db, Claim, Assignment, Document, Profile, PatientDetail,
    PatientAddress, ContactDetail, InsuredDetail, InsuranceDetail,
    IcdRecord, CptRecord, DocumentTag, ActivityLog
)
from backend.app.schemas.models import (
    ClaimSaveRequest, ClaimResponse
)
from backend.app.api.auth import get_current_user
from backend.app.api.assignments import resolve_employee_ids

router = APIRouter(prefix="/claims", tags=["Claims"])

@router.get("", response_model=List[ClaimResponse])
def get_claims(
    search: Optional[str] = None,
    claim_id: Optional[str] = None,
    patient_name: Optional[str] = None,
    employee_id: Optional[str] = None,
    insurer: Optional[str] = None,
    claim_status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Claim)
    
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(or_(
            Claim.claim_id_display.ilike(s),
            Claim.patient_name.ilike(s),
            Claim.claim_number.ilike(s),
            Claim.policy_number.ilike(s),
            Claim.insurer.ilike(s)
        ))
    if claim_id:
        query = query.filter(Claim.claim_id_display.ilike(f"%{claim_id.strip()}%"))
    if patient_name:
        query = query.filter(Claim.patient_name.ilike(f"%{patient_name.strip()}%"))
    if employee_id:
        target_ids = resolve_employee_ids(db, employee_id)
        query = query.filter(Claim.employee_id.in_(target_ids))
    if insurer:
        query = query.filter(Claim.insurer.ilike(f"%{insurer.strip()}%"))
    if claim_status and claim_status != "All Statuses":
        query = query.filter(Claim.claim_status == claim_status)
        
    claims = query.order_by(Claim.created_at.desc()).all()
    results = []
    for c in claims:
        # Generate summary strings for ICD and CPT
        icd_codes = [r.icd_code for r in c.icd_records if r.icd_code]
        cpt_codes = [r.cpt_code for r in c.cpt_records if r.cpt_code]
        
        results.append(ClaimResponse(
            id=c.id,
            claim_id_display=c.claim_id_display,
            assignment_id=c.assignment_id,
            document_id=c.document_id,
            document_filename=c.document.original_filename if c.document else "Patient Document",
            employee_id=c.employee_id,
            employee_name=c.employee.full_name if c.employee else "Unknown",
            patient_name=c.patient_name,
            claim_number=c.claim_number,
            policy_number=c.policy_number,
            insurer=c.insurer,
            claim_status=c.claim_status,
            status_reason=c.status_reason,
            total_cpt_amount=c.total_cpt_amount,
            icd_codes_summary=", ".join(icd_codes) if icd_codes else "None",
            cpt_codes_summary=", ".join(cpt_codes) if cpt_codes else "None",
            submitted_at=c.submitted_at,
            created_at=c.created_at,
            updated_at=c.updated_at
        ))
    return results

@router.get("/by-document/{document_id}")
def get_claim_by_document(document_id: str, db: Session = Depends(get_db)):
    """Fetch existing claim associated with document or return empty draft state"""
    claim = db.query(Claim).filter(Claim.document_id == document_id).first()
    if not claim:
        return None
    return get_claim_details(claim.id, db)

@router.get("/{claim_id}")
def get_claim_details(claim_id: str, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter(or_(Claim.id == claim_id, Claim.claim_id_display == claim_id)).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    # Gather tagged docs
    tags = db.query(DocumentTag).filter(DocumentTag.document_id == claim.document_id).all() if claim.document_id else []
    
    # Gather activity logs
    logs = db.query(ActivityLog).filter(
        or_(ActivityLog.claim_id == claim.id, ActivityLog.document_id == claim.document_id)
    ).order_by(ActivityLog.created_at.desc()).all()

    return {
        "id": claim.id,
        "claim_id_display": claim.claim_id_display,
        "assignment_id": claim.assignment_id,
        "document_id": claim.document_id,
        "document_filename": claim.document.original_filename if claim.document else "",
        "employee_id": claim.employee_id,
        "employee_name": claim.employee.full_name if claim.employee else "Unknown",
        "claim_status": claim.claim_status,
        "status_reason": claim.status_reason,
        "total_cpt_amount": claim.total_cpt_amount,
        "submitted_at": claim.submitted_at,
        "created_at": claim.created_at,
        "updated_at": claim.updated_at,
        "patient": {
            "initial": claim.patient_detail.initial if claim.patient_detail else "Mr",
            "first_name": claim.patient_detail.first_name if claim.patient_detail else "",
            "last_name": claim.patient_detail.last_name if claim.patient_detail else "",
            "ssn": claim.patient_detail.ssn if claim.patient_detail else "",
            "dob": claim.patient_detail.dob if claim.patient_detail else "",
            "gender": claim.patient_detail.gender if claim.patient_detail else "Male"
        },
        "address": {
            "address1": claim.patient_address.address1 if claim.patient_address else "",
            "address2": claim.patient_address.address2 if claim.patient_address else "",
            "zip": claim.patient_address.zip if claim.patient_address else "",
            "state": claim.patient_address.state if claim.patient_address else "NY",
            "county": claim.patient_address.county if claim.patient_address else "Queens",
            "city": claim.patient_address.city if claim.patient_address else "New York",
            "address_type": claim.patient_address.address_type if claim.patient_address else "Home"
        },
        "contact": {
            "contact_type": claim.contact_details[0].contact_type if claim.contact_details else "Mobile",
            "contact_number": claim.contact_details[0].contact_number if claim.contact_details else "",
            "extension": claim.contact_details[0].extension if claim.contact_details else ""
        },
        "insured": {
            "same_as_patient": claim.insured_detail.same_as_patient if claim.insured_detail else True,
            "data": claim.insured_detail.insured_data_json if claim.insured_detail else {}
        },
        "insurance": {
            "insurer": claim.insurance_detail.insurer if claim.insurance_detail else "",
            "policy_number": claim.insurance_detail.policy_number if claim.insurance_detail else "",
            "claim_number": claim.insurance_detail.claim_number if claim.insurance_detail else "",
            "date_of_accident": claim.insurance_detail.date_of_accident if claim.insurance_detail else "",
            "historical_summary": {
                "total_bills_found": claim.insurance_detail.total_bills_found if claim.insurance_detail else 0,
                "total_bill_amount": claim.insurance_detail.total_bill_amount if claim.insurance_detail else 0.0,
                "first_dos": claim.insurance_detail.first_dos if claim.insurance_detail else "",
                "last_dos": claim.insurance_detail.last_dos if claim.insurance_detail else "",
                "last_intake_date": claim.insurance_detail.last_intake_date if claim.insurance_detail else ""
            }
        },
        "icd_records": [
            {
                "id": r.id,
                "treating_provider": r.treating_provider,
                "signing_provider": r.signing_provider,
                "icd_code": r.icd_code,
                "icd_description": r.icd_description,
                "source_page": r.source_page,
                "confidence": r.confidence
            } for r in claim.icd_records
        ],
        "cpt_records": [
            {
                "id": r.id,
                "serving_address": r.serving_address,
                "cpt_code": r.cpt_code,
                "cpt_amount": r.cpt_amount,
                "cpt_description": r.cpt_description,
                "dos_start": r.dos_start,
                "dos_end": r.dos_end,
                "source_page": r.source_page,
                "confidence": r.confidence
            } for r in claim.cpt_records
        ],
        "tagged_documents": [
            {
                "id": t.id,
                "tag_name": t.tag_name,
                "start_page": t.start_page,
                "end_page": t.end_page,
                "page_count": t.page_count,
                "generated_storage_path": t.generated_storage_path,
                "created_at": t.created_at
            } for t in tags
        ],
        "activity_logs": [
            {
                "id": l.id,
                "user_name": l.user_name,
                "action": l.action,
                "details": l.details,
                "created_at": l.created_at
            } for l in logs
        ]
    }

@router.post("/save")
def save_or_submit_claim(
    req: ClaimSaveRequest,
    current_user: Profile = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Saves a draft claim or submits a completed claim.
    Updates patient details, addresses, contact, insured, insurance, ICDs, CPTs,
    and updates assignment status accordingly.
    """
    # Find existing claim by document_id or assignment_id
    claim = None
    if req.document_id:
        claim = db.query(Claim).filter(Claim.document_id == req.document_id).first()
    if not claim and req.assignment_id:
        claim = db.query(Claim).filter(Claim.assignment_id == req.assignment_id).first()
        
    p_name = f"{req.patient.first_name} {req.patient.last_name}".strip()
    cpt_total = sum(c.cpt_amount for c in req.cpt_records)
    
    if not claim:
        # Generate new claim ID display
        claim_count = db.query(Claim).count() + 1
        claim_id_display = f"CLM-2026-{claim_count:03d}"
        
        claim = Claim(
            claim_id_display=claim_id_display,
            assignment_id=req.assignment_id,
            employee_id=current_user.id,
            document_id=req.document_id,
            patient_name=p_name,
            claim_number=req.insurance.claim_number,
            policy_number=req.insurance.policy_number,
            insurer=req.insurance.insurer,
            claim_status="Pending" if req.is_draft else (req.claim_status or "Submitted"),
            status_reason=req.status_reason or "",
            total_cpt_amount=cpt_total,
            submitted_at=None if req.is_draft else datetime.datetime.utcnow()
        )
        db.add(claim)
        db.commit()
        db.refresh(claim)
    else:
        # Update existing claim
        claim.patient_name = p_name
        claim.claim_number = req.insurance.claim_number
        claim.policy_number = req.insurance.policy_number
        claim.insurer = req.insurance.insurer
        claim.total_cpt_amount = cpt_total
        claim.status_reason = req.status_reason or ""
        
        if req.is_draft:
            claim.claim_status = "Pending"
        else:
            claim.claim_status = req.claim_status or "Submitted"
            claim.submitted_at = datetime.datetime.utcnow()

    # Update Patient Details
    if not claim.patient_detail:
        claim.patient_detail = PatientDetail(claim_id=claim.id)
    claim.patient_detail.initial = req.patient.initial
    claim.patient_detail.first_name = req.patient.first_name
    claim.patient_detail.last_name = req.patient.last_name
    claim.patient_detail.ssn = req.patient.ssn
    claim.patient_detail.dob = req.patient.dob
    claim.patient_detail.gender = req.patient.gender

    # Update Address
    if not claim.patient_address:
        claim.patient_address = PatientAddress(claim_id=claim.id)
    claim.patient_address.address1 = req.address.address1
    claim.patient_address.address2 = req.address.address2
    claim.patient_address.zip = req.address.zip
    claim.patient_address.state = req.address.state
    claim.patient_address.county = req.address.county
    claim.patient_address.city = req.address.city
    claim.patient_address.address_type = req.address.address_type

    # Update Contact
    if not claim.contact_details:
        cd = ContactDetail(claim_id=claim.id)
        claim.contact_details.append(cd)
    else:
        cd = claim.contact_details[0]
    cd.contact_type = req.contact.contact_type
    cd.contact_number = req.contact.contact_number
    cd.extension = req.contact.extension

    # Update Insured Details
    if not claim.insured_detail:
        claim.insured_detail = InsuredDetail(claim_id=claim.id)
    claim.insured_detail.same_as_patient = req.insured.same_as_patient
    claim.insured_detail.insured_data_json = req.insured.dict()

    # Update Insurance
    if not claim.insurance_detail:
        claim.insurance_detail = InsuranceDetail(claim_id=claim.id)
    claim.insurance_detail.insurer = req.insurance.insurer
    claim.insurance_detail.policy_number = req.insurance.policy_number
    claim.insurance_detail.claim_number = req.insurance.claim_number
    claim.insurance_detail.date_of_accident = req.insurance.date_of_accident
    claim.insurance_detail.total_bills_found = req.insurance.total_bills_found
    claim.insurance_detail.total_bill_amount = req.insurance.total_bill_amount

    # Update ICD Records (delete old, insert new)
    db.query(IcdRecord).filter(IcdRecord.claim_id == claim.id).delete()
    for icd in req.icd_records:
        if icd.icd_code or icd.icd_description:
            rec = IcdRecord(
                claim_id=claim.id,
                treating_provider=icd.treating_provider,
                signing_provider=icd.signing_provider,
                icd_code=icd.icd_code,
                icd_description=icd.icd_description,
                source_page=icd.source_page,
                confidence=icd.confidence
            )
            db.add(rec)

    # Update CPT Records (delete old, insert new)
    db.query(CptRecord).filter(CptRecord.claim_id == claim.id).delete()
    for cpt in req.cpt_records:
        if cpt.cpt_code or cpt.cpt_description:
            rec = CptRecord(
                claim_id=claim.id,
                serving_address=cpt.serving_address,
                cpt_code=cpt.cpt_code,
                cpt_amount=cpt.cpt_amount,
                cpt_description=cpt.cpt_description,
                dos_start=cpt.dos_start,
                dos_end=cpt.dos_end,
                source_page=cpt.source_page,
                confidence=cpt.confidence
            )
            db.add(rec)

    # Update assignment status if present
    asg = None
    if req.assignment_id:
        asg = db.query(Assignment).filter(Assignment.id == req.assignment_id).first()
    elif req.document_id:
        asg = db.query(Assignment).filter(Assignment.document_id == req.document_id).first()

    if asg:
        if req.is_draft:
            asg.status = "In Progress"
        else:
            asg.status = "Completed"

    action_label = "Claim Draft Saved" if req.is_draft else f"Claim Submitted ({claim.claim_status})"
    details_text = f"Patient: {p_name}, Total Billed: ${cpt_total:.2f}. Status: {claim.claim_status}."
    if claim.status_reason:
        details_text += f" Reason: {claim.status_reason}"

    log = ActivityLog(
        user_id=current_user.id,
        user_name=current_user.full_name,
        claim_id=claim.id,
        document_id=req.document_id,
        action=action_label,
        details=details_text
    )
    db.add(log)
    db.commit()
    db.refresh(claim)

    return {
        "message": "Claim saved successfully as draft" if req.is_draft else "Claim submitted successfully!",
        "claim_id": claim.id,
        "claim_id_display": claim.claim_id_display,
        "claim_status": claim.claim_status,
        "patient_name": claim.patient_name
    }

