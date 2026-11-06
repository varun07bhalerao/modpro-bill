import datetime
import uuid
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from backend.app.core.config import settings

Base = declarative_base()

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Profile(Base):
    __tablename__ = "profiles"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(50), nullable=False, default="employee") # admin | employee
    password_hash = Column(String(255), nullable=False)
    avatar_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Folder(Base):
    __tablename__ = "folders"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    folder_name = Column(String(255), nullable=False)
    uploaded_by = Column(String(64), ForeignKey("profiles.id"), nullable=False)
    total_files = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    documents = relationship("Document", back_populates="folder", cascade="all, delete-orphan")
    uploader = relationship("Profile")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    folder_id = Column(String(64), ForeignKey("folders.id"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    total_pages = Column(Integer, default=1)
    uploaded_by = Column(String(64), ForeignKey("profiles.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    folder = relationship("Folder", back_populates="documents")
    assignments = relationship("Assignment", back_populates="document", cascade="all, delete-orphan")
    tags = relationship("DocumentTag", back_populates="document", cascade="all, delete-orphan")

class Assignment(Base):
    __tablename__ = "assignments"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    document_id = Column(String(64), ForeignKey("documents.id"), nullable=False)
    employee_id = Column(String(64), ForeignKey("profiles.id"), nullable=False)
    assigned_by = Column(String(64), ForeignKey("profiles.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)
    priority = Column(String(20), default="Normal") # Normal | High
    status = Column(String(50), default="Assigned") # Unassigned | Assigned | In Progress | Pending Review | Completed
    instructions = Column(Text, nullable=True)

    document = relationship("Document", back_populates="assignments")
    employee = relationship("Profile", foreign_keys=[employee_id])
    assigner = relationship("Profile", foreign_keys=[assigned_by])
    claim = relationship("Claim", back_populates="assignment", uselist=False)

class Claim(Base):
    __tablename__ = "claims"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    assignment_id = Column(String(64), ForeignKey("assignments.id"), nullable=True)
    employee_id = Column(String(64), ForeignKey("profiles.id"), nullable=False)
    document_id = Column(String(64), ForeignKey("documents.id"), nullable=True)
    
    claim_id_display = Column(String(64), unique=True, nullable=False) # e.g. CLM-2026-001
    patient_name = Column(String(255), default="")
    claim_number = Column(String(100), default="")
    policy_number = Column(String(100), default="")
    insurer = Column(String(255), default="")
    
    claim_status = Column(String(100), default="New Case") 
    # Options:
    # 1. Issue - 45 Days Crossed
    # 2. Issue - Already Billed
    # 3. Issue - CPT and Charges Missing
    # 4. Issue - ICDs Missing
    # 5. Issue - Reports Missing
    # 6. New Case
    # 7. Pending
    # 8. Returned
    # 9. Submitted
    status_reason = Column(Text, default="")
    extraction_status = Column(String(50), default="pending") # pending | in_progress | completed | failed
    
    total_cpt_amount = Column(Float, default=0.0)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    assignment = relationship("Assignment", back_populates="claim")
    employee = relationship("Profile", foreign_keys=[employee_id])
    document = relationship("Document")

    patient_detail = relationship("PatientDetail", back_populates="claim", uselist=False, cascade="all, delete-orphan")
    patient_address = relationship("PatientAddress", back_populates="claim", uselist=False, cascade="all, delete-orphan")
    contact_details = relationship("ContactDetail", back_populates="claim", cascade="all, delete-orphan")
    insured_detail = relationship("InsuredDetail", back_populates="claim", uselist=False, cascade="all, delete-orphan")
    insurance_detail = relationship("InsuranceDetail", back_populates="claim", uselist=False, cascade="all, delete-orphan")
    icd_records = relationship("IcdRecord", back_populates="claim", cascade="all, delete-orphan")
    cpt_records = relationship("CptRecord", back_populates="claim", cascade="all, delete-orphan")
    tags = relationship("DocumentTag", back_populates="claim", cascade="all, delete-orphan")
    extraction_result = relationship("ExtractionResult", back_populates="claim", uselist=False, cascade="all, delete-orphan")
    provenances = relationship("FieldProvenance", back_populates="claim", cascade="all, delete-orphan")

class PatientDetail(Base):
    __tablename__ = "patient_details"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    claim_id = Column(String(64), ForeignKey("claims.id"), nullable=False)
    initial = Column(String(20), default="Mr") # Sal / Initial
    first_name = Column(String(100), default="")
    last_name = Column(String(100), default="")
    ssn = Column(String(50), default="")
    dob = Column(String(50), default="") # dd-mm-yyyy
    gender = Column(String(20), default="Male") # Male | Female | Other

    claim = relationship("Claim", back_populates="patient_detail")

class PatientAddress(Base):
    __tablename__ = "patient_addresses"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    claim_id = Column(String(64), ForeignKey("claims.id"), nullable=False)
    address1 = Column(String(255), default="")
    address2 = Column(String(255), default="")
    zip = Column(String(20), default="")
    state = Column(String(50), default="NY")
    county = Column(String(100), default="Queens")
    city = Column(String(100), default="New York")
    address_type = Column(String(50), default="Home") # Home | Other

    claim = relationship("Claim", back_populates="patient_address")

class ContactDetail(Base):
    __tablename__ = "contact_details"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    claim_id = Column(String(64), ForeignKey("claims.id"), nullable=False)
    contact_type = Column(String(50), default="Mobile") # Mobile | Home | Work
    contact_number = Column(String(50), default="")
    extension = Column(String(20), default="")

    claim = relationship("Claim", back_populates="contact_details")

class InsuredDetail(Base):
    __tablename__ = "insured_details"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    claim_id = Column(String(64), ForeignKey("claims.id"), nullable=False)
    same_as_patient = Column(Boolean, default=True)
    insured_data_json = Column(JSON, default=dict)

    claim = relationship("Claim", back_populates="insured_detail")

class InsuranceDetail(Base):
    __tablename__ = "insurance_details"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    claim_id = Column(String(64), ForeignKey("claims.id"), nullable=False)
    insurer = Column(String(255), default="")
    policy_number = Column(String(100), default="")
    claim_number = Column(String(100), default="")
    date_of_accident = Column(String(50), default="") # dd-mm-yyyy
    
    # Historical Summary
    total_bills_found = Column(Integer, default=0)
    total_bill_amount = Column(Float, default=0.0)
    first_dos = Column(String(50), default="")
    last_dos = Column(String(50), default="")
    last_intake_date = Column(String(50), default="")

    claim = relationship("Claim", back_populates="insurance_detail")

class IcdRecord(Base):
    __tablename__ = "icd_records"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    claim_id = Column(String(64), ForeignKey("claims.id"), nullable=False)
    treating_provider = Column(String(255), default="")
    signing_provider = Column(String(255), default="")
    icd_code = Column(String(50), default="")
    icd_description = Column(String(255), default="")
    source_page = Column(Integer, default=1)
    confidence = Column(Float, default=0.95)

    claim = relationship("Claim", back_populates="icd_records")

class CptRecord(Base):
    __tablename__ = "cpt_records"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    claim_id = Column(String(64), ForeignKey("claims.id"), nullable=False)
    serving_address = Column(String(255), default="")
    cpt_code = Column(String(50), default="")
    cpt_amount = Column(Float, default=0.0)
    cpt_description = Column(String(255), default="")
    dos_start = Column(String(50), default="")
    dos_end = Column(String(50), default="")
    source_page = Column(Integer, default=1)
    confidence = Column(Float, default=0.95)

    claim = relationship("Claim", back_populates="cpt_records")

class DocumentTag(Base):
    __tablename__ = "document_tags"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    document_id = Column(String(64), ForeignKey("documents.id"), nullable=False)
    claim_id = Column(String(64), ForeignKey("claims.id"), nullable=True)
    tag_name = Column(String(100), nullable=False) # AOB | Bills | DELIVERY RECEIPT | INVOICE | Medical Report | MISCELLANEOUS | NF-2
    start_page = Column(Integer, nullable=False)
    end_page = Column(Integer, nullable=False)
    page_count = Column(Integer, default=1)
    generated_storage_path = Column(String(500), nullable=True)
    created_by = Column(String(64), ForeignKey("profiles.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="tags")
    claim = relationship("Claim", back_populates="tags")
    creator = relationship("Profile")

class ExtractionResult(Base):
    __tablename__ = "extraction_results"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    claim_id = Column(String(64), ForeignKey("claims.id"), nullable=False)
    raw_extraction_json = Column(JSON, default=dict)
    validation_results = Column(JSON, default=dict)
    extraction_model = Column(String(100), default="demo-vision-model")
    extraction_status = Column(String(50), default="completed")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    claim = relationship("Claim", back_populates="extraction_result")

class FieldProvenance(Base):
    __tablename__ = "field_provenance"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    claim_id = Column(String(64), ForeignKey("claims.id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    extracted_value = Column(String(255), default="")
    source_document_id = Column(String(64), nullable=True)
    source_page = Column(Integer, default=1)
    confidence = Column(Float, default=0.95)
    employee_corrected = Column(Boolean, default=False)
    final_value = Column(String(255), default="")

    claim = relationship("Claim", back_populates="provenances")

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(String(64), primary_key=True, default=generate_uuid)
    user_id = Column(String(64), ForeignKey("profiles.id"), nullable=True)
    user_name = Column(String(255), default="System")
    claim_id = Column(String(64), nullable=True)
    document_id = Column(String(64), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# Reference Masters
class MasterICD(Base):
    __tablename__ = "master_icd"
    code = Column(String(50), primary_key=True)
    description = Column(String(255), nullable=False)

class MasterCPT(Base):
    __tablename__ = "master_cpt"
    code = Column(String(50), primary_key=True)
    description = Column(String(255), nullable=False)
    default_amount = Column(Float, default=150.0)

class MasterInsurer(Base):
    __tablename__ = "master_insurers"
    id = Column(String(64), primary_key=True, default=generate_uuid)
    name = Column(String(255), unique=True, nullable=False)
    phone = Column(String(50), default="")
    address = Column(String(255), default="")

class MasterProvider(Base):
    __tablename__ = "master_providers"
    id = Column(String(64), primary_key=True, default=generate_uuid)
    name = Column(String(255), unique=True, nullable=False)
    npi = Column(String(50), default="")
    specialty = Column(String(100), default="Chiropractic")

# Database session & init
if "sqlite" in settings.DATABASE_URL:
    try:
        Path(settings.DATABASE_URL.replace("sqlite:////", "/").replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)

