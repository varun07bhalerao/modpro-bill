import React, { useState, useEffect } from 'react';
import { 
  UserCheck, Users, FileText, CheckCircle2, AlertCircle, RefreshCw, 
  Clock, ShieldAlert, ArrowRight, Folder
} from 'lucide-react';
import { AssignmentItem, FolderItem, DocumentItem, User } from '../../types';
import { assignmentService } from '../../services/assignmentService';

export const EmployeeAssignmentPage: React.FC = () => {
  const [folders, setFolders] = useState<FolderItem[]>([]);
  const [employees, setEmployees] = useState<User[]>([]);
  const [assignments, setAssignments] = useState<AssignmentItem[]>([]);

  // Selection states
  const [selectedFolderId, setSelectedFolderId] = useState<string>('');
  const [selectedDocId, setSelectedDocId] = useState<string>('');
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('');
  const [priority, setPriority] = useState<'Normal' | 'High'>('Normal');
  const [instructions, setInstructions] = useState<string>('');

  // Reassign modal state
  const [reassignModalAsg, setReassignModalAsg] = useState<AssignmentItem | null>(null);
  const [reassignEmpId, setReassignEmpId] = useState<string>('');

  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [foldersRes, usersRes, asgRes] = await Promise.all([
        fetch('/api/folders'),
        fetch('/api/auth/users'),
        fetch('/api/assignments')
      ]);

      const foldersData = await foldersRes.json();
      const usersData = await usersRes.json();
      const asgData = await asgRes.json();

      setFolders(foldersData);
      setEmployees(usersData.filter((u: User) => u.role === 'employee'));
      setAssignments(asgData);

      if (foldersData.length > 0 && !selectedFolderId) {
        setSelectedFolderId(foldersData[0].id);
        if (foldersData[0].documents.length > 0) {
          setSelectedDocId(foldersData[0].documents[0].id);
        }
      }
    } catch (err: any) {
      console.error(err);
      setMessage({ type: 'error', text: 'Failed to load assignment data' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const currentFolder = folders.find(f => f.id === selectedFolderId);
  const currentDoc = currentFolder?.documents.find(d => d.id === selectedDocId);
  const selectedEmp = employees.find(e => e.id === selectedEmployeeId);

  // Automatically ensure valid document selected for the active folder
  useEffect(() => {
    if (folders.length > 0) {
      const activeFolder = folders.find(f => f.id === selectedFolderId) || folders[0];
      if (activeFolder) {
        if (!selectedFolderId || selectedFolderId !== activeFolder.id) {
          setSelectedFolderId(activeFolder.id);
        }
        const hasCurrentDoc = activeFolder.documents && activeFolder.documents.some(d => d.id === selectedDocId);
        if (!hasCurrentDoc) {
          const unassigned = activeFolder.documents?.find(d => d.assignment_status === 'Unassigned');
          setSelectedDocId(unassigned ? unassigned.id : (activeFolder.documents?.[0]?.id || ''));
        }
      }
    }
  }, [folders, selectedFolderId]);

  const handleFolderChange = (fId: string) => {
    setSelectedFolderId(fId);
    const f = folders.find(item => item.id === fId);
    if (f && f.documents && f.documents.length > 0) {
      const unassigned = f.documents.find(d => d.assignment_status === 'Unassigned');
      setSelectedDocId(unassigned ? unassigned.id : f.documents[0].id);
    } else {
      setSelectedDocId('');
    }
  };

  const handleAssignSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);

    if (!selectedFolderId || !selectedDocId || !selectedEmployeeId) {
      setMessage({ type: 'error', text: 'Please select folder, document and employee.' });
      return;
    }

    setSubmitting(true);
    const token = localStorage.getItem('billnexa_token');

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch('/api/assignments/assign', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          folder_id: selectedFolderId,
          document_id: selectedDocId,
          employee_id: selectedEmployeeId,
          priority,
          instructions
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Assignment failed');
      }

      // Sync with Supabase document_assignments if configured
      try {
        await assignmentService.assignDocument(selectedDocId, selectedEmployeeId, undefined, priority);
      } catch (syncErr) {
        console.warn('Supabase sync note:', syncErr);
      }

      setMessage({
        type: 'success',
        text: `Successfully assigned ${currentDoc?.original_filename || 'document'} to ${selectedEmp?.full_name || 'employee'}.`
      });
      setInstructions('');
      fetchData();
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Assignment failed' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleReassignSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reassignModalAsg || !reassignEmpId) return;

    const token = localStorage.getItem('billnexa_token');
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch('/api/assignments/reassign', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          assignment_id: reassignModalAsg.id,
          new_employee_id: reassignEmpId
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Reassignment failed');
      }

      setReassignModalAsg(null);
      setMessage({ type: 'success', text: 'Document reassigned successfully.' });
      fetchData();
    } catch (err: any) {
      alert(err.message || 'Reassignment failed');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <UserCheck size={22} className="text-blue-600" />
          Employee Assignment Module
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Select pre-sorted folders and allocate individual patient PDFs to employees. Assignment must be performed per PDF.
        </p>
      </div>

      {message && (
        <div className={`p-3 rounded-lg text-xs font-semibold flex items-center gap-2 ${
          message.type === 'success'
            ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
            : 'bg-rose-50 border border-rose-200 text-rose-700'
        }`}>
          {message.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Main Assignment Form (Top) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5">
        <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center gap-2">
          <span>New Document Assignment</span>
          <span className="text-[10px] text-blue-600 font-semibold px-2 py-0.5 bg-blue-50 rounded">
            Step-by-Step
          </span>
        </h2>

        <form onSubmit={handleAssignSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 1. Folder Selection */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                1. Select Folder
              </label>
              <select
                value={selectedFolderId}
                onChange={(e) => handleFolderChange(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {folders.map(f => (
                  <option key={f.id} value={f.id}>
                    {f.folder_name} ({f.total_files} files)
                  </option>
                ))}
              </select>
            </div>

            {/* 2. PDF Document Selection */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                2. Select PDF Document
              </label>
              <select
                value={selectedDocId}
                onChange={(e) => setSelectedDocId(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
              >
                {!currentFolder?.documents || currentFolder.documents.length === 0 ? (
                  <option value="">-- No documents in this folder --</option>
                ) : (
                  currentFolder.documents.map(d => (
                    <option key={d.id} value={d.id}>
                      {d.original_filename} ({d.total_pages} pages) - [{d.assignment_status}]
                    </option>
                  ))
                )}
              </select>
            </div>

            {/* 3. Employee Selection */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                3. Select Employee
              </label>
              <select
                value={selectedEmployeeId}
                onChange={(e) => setSelectedEmployeeId(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                required
              >
                <option value="">-- Choose Employee --</option>
                {employees.map(emp => (
                  <option key={emp.id} value={emp.id}>
                    {emp.full_name} ({emp.email})
                  </option>
                ))}
              </select>
            </div>

            {/* 4. Priority */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as 'Normal' | 'High')}
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Normal">Normal Priority</option>
                <option value="High">High Priority (Expedited)</option>
              </select>
            </div>
          </div>

          {/* Optional Instructions */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Optional Instructions / Intake Notes
            </label>
            <input
              type="text"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g. Check handwritten ICD codes in clinical evaluation page and verify AOB signature."
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Submit Button */}
          <div className="flex items-center justify-between pt-2">
            <span className="text-[11px] text-slate-500">
              Assigned documents will immediately appear in the employee's "My Assigned Documents" task view.
            </span>
            <button
              type="submit"
              disabled={submitting || !selectedEmployeeId}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg transition shadow-sm flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {submitting ? 'Assigning...' : 'Assign Document'}
              <ArrowRight size={14} />
            </button>
          </div>
        </form>
      </div>

      {/* Assignment Table (Bottom) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
            <Users size={16} className="text-blue-600" />
            Current Employee Assignments ({assignments.length})
          </h2>
          <button
            onClick={fetchData}
            className="text-xs text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1"
          >
            <RefreshCw size={12} /> Refresh
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200 uppercase text-[10px]">
              <tr>
                <th className="py-2.5 px-4">File Name</th>
                <th className="py-2.5 px-4">Folder</th>
                <th className="py-2.5 px-4">Assigned Employee</th>
                <th className="py-2.5 px-4">Assigned Date</th>
                <th className="py-2.5 px-4">Priority</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {assignments.map(asg => (
                <tr key={asg.id} className="hover:bg-slate-50/80 transition">
                  <td className="py-3 px-4 font-bold text-slate-900 flex items-center gap-2">
                    <FileText size={15} className="text-blue-600 shrink-0" />
                    {asg.document_filename}
                    <span className="text-[10px] text-slate-400 font-normal">
                      ({asg.total_pages}p)
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-600">{asg.folder_name}</td>
                  <td className="py-3 px-4">
                    <div className="font-bold text-slate-900">{asg.employee_name}</div>
                    <div className="text-[10px] text-slate-400">{asg.employee_email}</div>
                  </td>
                  <td className="py-3 px-4 text-slate-500">
                    {new Date(asg.assigned_at).toLocaleDateString()}
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      asg.priority === 'High'
                        ? 'bg-rose-50 text-rose-700 border border-rose-200'
                        : 'bg-slate-100 text-slate-700'
                    }`}>
                      {asg.priority}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                      asg.status === 'Completed'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : asg.status === 'In Progress'
                        ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                        : 'bg-blue-50 text-blue-700 border-blue-200'
                    }`}>
                      {asg.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    {asg.status !== 'Completed' ? (
                      <button
                        onClick={() => {
                          setReassignModalAsg(asg);
                          setReassignEmpId(asg.employee_id);
                        }}
                        className="px-2.5 py-1 text-slate-700 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded text-xs font-semibold transition"
                      >
                        Reassign
                      </button>
                    ) : (
                      <span className="text-[11px] text-emerald-700 font-semibold">Submitted</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Reassign Modal */}
      {reassignModalAsg && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-md p-5 space-y-4">
            <h3 className="text-sm font-bold text-slate-900">
              Reassign Document: {reassignModalAsg.document_filename}
            </h3>
            <p className="text-xs text-slate-500">
              Currently assigned to <b>{reassignModalAsg.employee_name}</b>. Select another employee:
            </p>

            <select
              value={reassignEmpId}
              onChange={(e) => setReassignEmpId(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded-lg p-2"
            >
              {employees.map(emp => (
                <option key={emp.id} value={emp.id}>
                  {emp.full_name} ({emp.email})
                </option>
              ))}
            </select>

            <div className="flex justify-end space-x-2 pt-2">
              <button
                type="button"
                onClick={() => setReassignModalAsg(null)}
                className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleReassignSubmit}
                className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg shadow-xs"
              >
                Confirm Reassignment
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

