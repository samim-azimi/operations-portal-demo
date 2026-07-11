import { CheckCircle2, Download, FileCheck2, FilePlus2, FileSignature, Search, Send, ShieldCheck, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { api, apiBlob, downloadProtected } from "../api";
import { useAuth } from "../auth";
import { Badge, ErrorBox, Loading, fmt } from "../components/UI";
import { canAccess } from "../modules";

const statuses=["","draft","pending","in_progress","completed","rejected","returned","cancelled"];

export default function Sign(){
  return <Routes>
    <Route index element={<SignDashboard/>}/>
    <Route path="envelopes" element={<SignDashboard/>}/>
    <Route path="envelopes/:id" element={<EnvelopeDetail/>}/>
    <Route path="review/:token" element={<ReviewSign/>}/>
    <Route path="verify" element={<VerifyDocument/>}/>
  </Routes>;
}

function SignDashboard(){
  const {user}=useAuth(); const navigate=useNavigate();
  const canCreate=canAccess(user,"can_create_signature_envelope");
  const [data,setData]=useState(null); const [users,setUsers]=useState([]);
  const [query,setQuery]=useState(""); const [status,setStatus]=useState("");
  const [error,setError]=useState(""); const [creating,setCreating]=useState(false);
  const [form,setForm]=useState({title:"",document_type:"general_document",document_reference_id:"",subject:"",message:"",file:null,recipientIds:[]});
  async function load(){
    setError("");
    try{
      const params=new URLSearchParams({page:"1",page_size:"50"});
      if(query)params.set("q",query);if(status)params.set("status",status);
      const result=await api(`/sign/envelopes?${params}`);setData(result);
      if(canCreate&&!users.length)setUsers(await api("/sign/users"));
    }catch(err){setError(err.message);}
  }
  useEffect(()=>{load();},[status]);
  async function create(event){
    event.preventDefault();setCreating(true);setError("");
    try{
      const metadata={
        title:form.title,document_type:form.document_type,
        document_reference_id:form.document_reference_id||null,
        subject:form.subject||null,message:form.message||null,routing_mode:"sequential",
        recipients:form.recipientIds.map((id,index)=>({user_id:Number(id),routing_order:index+1,role_name:users.find(item=>item.id===Number(id))?.role.replaceAll("_"," ")})),
      };
      const body=new FormData();body.append("metadata",JSON.stringify(metadata));body.append("file",form.file);
      const created=await api("/sign/envelopes",{method:"POST",body});
      navigate(`/sign/envelopes/${created.id}`);
    }catch(err){setError(err.message);}finally{setCreating(false);}
  }
  const counts=useMemo(()=>{
    const items=data?.items||[];
    return {pending:items.filter(item=>["pending","in_progress"].includes(item.status)).length,completed:items.filter(item=>item.status==="completed").length,returned:items.filter(item=>["rejected","returned"].includes(item.status)).length};
  },[data]);
  if(!data&&!error)return <Loading/>;
  return <div className="sign-page">
    <div className="pagehead"><div><span className="eyebrow">Secure internal approvals</span><h1>Digital Signature</h1><p>Send, sign, verify, and retain organizational PDF approvals.</p></div><div className="actions"><Link className="secondary" to="/profile/signature"><FileSignature size={16}/>My signature</Link><Link className="secondary" to="/sign/verify"><ShieldCheck size={16}/>Verify</Link></div></div>
    <ErrorBox error={error}/>
    <div className="sign-stat-grid"><article><Send/><span>Pending signatures<strong>{counts.pending}</strong></span></article><article><CheckCircle2/><span>Completed<strong>{counts.completed}</strong></span></article><article><XCircle/><span>Rejected / returned<strong>{counts.returned}</strong></span></article></div>
    {canCreate&&<details className="panel sign-create-panel"><summary><FilePlus2/>Create signing envelope</summary><form onSubmit={create}>
      <div className="grid three"><label>Document title<input required value={form.title} onChange={e=>setForm({...form,title:e.target.value})}/></label><label>Document type<select value={form.document_type} onChange={e=>setForm({...form,document_type:e.target.value})}>{["general_document","purchase_request","purchase_order","stock_document","contract"].map(item=><option key={item} value={item}>{item.replaceAll("_"," ")}</option>)}</select></label><label>Reference ID<input placeholder="PR-2026-0007" value={form.document_reference_id} onChange={e=>setForm({...form,document_reference_id:e.target.value})}/></label></div>
      <div className="grid two"><label>Email subject<input value={form.subject} onChange={e=>setForm({...form,subject:e.target.value})}/></label><label>PDF document<input required type="file" accept=".pdf,application/pdf" onChange={e=>setForm({...form,file:e.target.files[0]||null})}/></label></div>
      <label>Message<textarea rows="2" value={form.message} onChange={e=>setForm({...form,message:e.target.value})}/></label>
      <fieldset><legend>Sequential signers</legend><p className="form-help">Select signers in the order they should receive the document.</p><div className="signer-picker">{users.map(person=><label key={person.id}><input type="checkbox" checked={form.recipientIds.includes(String(person.id))} onChange={e=>setForm({...form,recipientIds:e.target.checked?[...form.recipientIds,String(person.id)]:form.recipientIds.filter(id=>id!==String(person.id))})}/><span>{person.full_name}<small>{person.email}</small></span>{form.recipientIds.includes(String(person.id))&&<b>{form.recipientIds.indexOf(String(person.id))+1}</b>}</label>)}</div></fieldset>
      <button className="primary" disabled={creating||!form.file||!form.recipientIds.length}>{creating?"Creating...":"Create draft envelope"}</button>
    </form></details>}
    <section className="panel">
      <div className="sign-toolbar"><div className="stock-search"><Search/><input placeholder="Envelope ID, title, or reference" value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>e.key==="Enter"&&load()}/></div><select value={status} onChange={e=>setStatus(e.target.value)}>{statuses.map(item=><option key={item} value={item}>{item?item.replaceAll("_"," "):"All statuses"}</option>)}</select><button className="secondary" onClick={load}>Search</button></div>
      <div className="tablewrap"><table><thead><tr><th>Envelope</th><th>Document</th><th>Status</th><th>Signers</th><th>Created</th></tr></thead><tbody>{(data?.items||[]).map(item=><tr key={item.id}><td><Link to={`/sign/envelopes/${item.id}`}><strong>{item.envelope_id}</strong></Link><span>{item.document_reference_id}</span></td><td>{item.title}<span>{item.document_type.replaceAll("_"," ")}</span></td><td><Badge>{item.status.replaceAll("_"," ")}</Badge></td><td>{item.recipients.filter(r=>r.status==="signed").length}/{item.recipients.length}</td><td>{fmt(item.created_at)}</td></tr>)}</tbody></table></div>
      {!data?.items.length&&<div className="quiet-state"><FileCheck2/><p>No signing envelopes match this view.</p></div>}
    </section>
  </div>;
}

function EnvelopeDetail(){
  const {id}=useParams();const {user}=useAuth();const navigate=useNavigate();
  const [envelope,setEnvelope]=useState(null);const [audit,setAudit]=useState([]);const [error,setError]=useState("");const [message,setMessage]=useState("");
  async function load(){try{const [detail,trail]=await Promise.all([api(`/sign/envelopes/${id}`),api(`/sign/envelopes/${id}/audit`)]);setEnvelope(detail);setAudit(trail);}catch(err){setError(err.message);}}
  useEffect(()=>{load();},[id]);
  async function send(){try{const result=await api(`/sign/envelopes/${id}/send`,{method:"POST"});setMessage(result.signing_url?`Development signing link: ${result.signing_url}`:"Envelope sent.");load();}catch(err){setError(err.message);}}
  async function reviewAndSign(){try{const result=await api(`/sign/envelopes/${id}/my-review-link`,{method:"POST"});navigate(result.review_path);}catch(err){setError(err.message);}}
  async function cancel(){try{await api(`/sign/envelopes/${id}/cancel`,{method:"POST"});setMessage("Envelope cancelled.");load();}catch(err){setError(err.message);}}
  if(!envelope&&!error)return <Loading/>;
  const myRecipient=envelope?.recipients.find(item=>item.user_id===user.id);
  return <div className="sign-page"><Link className="back" to="/sign">← Back to Sign</Link><ErrorBox error={error}/>{message&&<div className="alert success sign-link-message">{message}</div>}{envelope&&<>
    <div className="pagehead"><div><span className="eyebrow">{envelope.envelope_id}</span><h1>{envelope.title}</h1><p>{envelope.document_type.replaceAll("_"," ")} · SHA256 {envelope.current_document_hash.slice(0,16)}...</p></div><div className="actions">{myRecipient&&["sent","viewed"].includes(myRecipient.status)&&<button className="primary" onClick={reviewAndSign}><FileSignature size={15}/>Review & Sign</button>}{envelope.status==="draft"&&canAccess(user,"can_send_signature_envelope")&&<button className="primary" onClick={send}><Send size={15}/>Send</button>}{!["completed","rejected","cancelled"].includes(envelope.status)&&canAccess(user,"can_cancel_signature_envelope")&&<button className="ghost danger" onClick={cancel}>Cancel</button>}</div></div>
    <div className="sign-detail-grid"><section className="panel"><div className="panel-title"><h2>Signing route</h2><Badge>{envelope.status}</Badge></div><div className="recipient-timeline">{envelope.recipients.map(item=><article key={item.id} className={item.status}><b>{item.routing_order}</b><div><strong>{item.full_name}</strong><span>{item.email} · {item.role_name||"Signer"}</span>{item.verification_number&&<code>{item.verification_number}</code>}</div><Badge>{item.status}</Badge></article>)}</div><div className="actions"><button className="secondary" onClick={()=>downloadProtected(`/sign/envelopes/${id}/download-original`,`${envelope.envelope_id}_original.pdf`)}><Download size={15}/>Original</button>{envelope.final_signed_pdf_hash&&<button className="secondary" onClick={()=>downloadProtected(`/sign/envelopes/${id}/download-signed`,`${envelope.envelope_id}_signed.pdf`)}><Download size={15}/>Signed PDF</button>}</div></section>
    <section className="panel"><div className="panel-title"><h2>Audit trail</h2><ShieldCheck/></div><div className="sign-audit">{audit.map(item=><article key={item.id}><i/><div><strong>{item.action}</strong><span>{fmt(item.created_at)}{item.ip_address?` · ${item.ip_address}`:""}</span></div></article>)}</div></section></div>
  </>}</div>;
}

function ReviewSign(){
  const {token}=useParams();const navigate=useNavigate();
  const [data,setData]=useState(null);const [pdfUrl,setPdfUrl]=useState("");const [signatureUrl,setSignatureUrl]=useState("");const [signOpen,setSignOpen]=useState(false);const [confirmed,setConfirmed]=useState(false);const [comment,setComment]=useState("");const [error,setError]=useState("");const [busy,setBusy]=useState(false);
  useEffect(()=>{const urls=[];(async()=>{try{const review=await api(`/sign/review/${token}`);setData(review);await api(`/sign/review/${token}/viewed`,{method:"POST"});const blob=await apiBlob(`/sign/review/${token}/document`);const documentUrl=URL.createObjectURL(blob);urls.push(documentUrl);setPdfUrl(documentUrl);try{const signature=await apiBlob("/sign/profile/signature/file");const imageUrl=URL.createObjectURL(signature);urls.push(imageUrl);setSignatureUrl(imageUrl);}catch{/* Typed signature remains available. */}}catch(err){setError(err.message);}})();return()=>urls.forEach(url=>URL.revokeObjectURL(url));},[token]);
  async function act(action){setBusy(true);setError("");try{const body=action==="sign"?{confirmed_review:confirmed,typed_name:data.recipient.full_name}:{comment};const result=await api(`/sign/review/${token}/${action}`,{method:"POST",body:JSON.stringify(body)});navigate(`/sign/envelopes/${data.envelope.id}`,{state:{result}});}catch(err){setError(err.message);}finally{setBusy(false);}}
  if(!data&&!error)return <Loading/>;
  const field=data?.recipient;
  const hotspotStyle=field?{left:`${field.signature_x*100}%`,bottom:`${field.signature_y*100}%`,width:`${field.signature_width*100}%`,height:`${field.signature_height*100}%`}:{};
  return <div className="sign-page"><ErrorBox error={error}/>{data&&<><div className="pagehead"><div><span className="eyebrow">{data.envelope.envelope_id}</span><h1>Review and sign</h1><p>{data.envelope.title} · Assigned to {data.recipient.full_name}</p></div></div><div className="review-layout"><section className="panel pdf-review">{pdfUrl?<><iframe title="Document review" src={pdfUrl}/><button className="signature-hotspot" style={hotspotStyle} onClick={()=>setSignOpen(true)}><FileSignature/><span>Click to sign here<small>{field.signature_page===-1?"Final page":`Page ${field.signature_page}`}</small></span></button></>:<Loading/>}</section><aside className="panel sign-action-panel"><FileSignature/><h2>Your signature</h2><p>The PDF is open inside the portal. Review it, then click the highlighted signature area on the document.</p><button className="primary locate-signature" disabled={!pdfUrl} onClick={()=>setSignOpen(true)}><FileSignature/>Review signature</button><div className="sign-proof-note"><ShieldCheck/><span>Your organizational account, time, IP address, browser, verification number, and document hash are recorded.</span></div><textarea rows="4" placeholder="Required comment for reject or return" value={comment} onChange={e=>setComment(e.target.value)}/><button className="ghost danger" disabled={busy||comment.trim().length<2} onClick={()=>act("reject")}>Reject</button><button className="secondary" disabled={busy||comment.trim().length<2} onClick={()=>act("return")}>Return for correction</button></aside></div>
    {signOpen&&<div className="modal-backdrop"><section className="modal-card signature-confirmation" role="dialog" aria-modal="true" aria-label="Confirm digital signature"><div className="panel-title"><div><span className="eyebrow">Secure signature</span><h2>Confirm your signature</h2></div><button className="icon" onClick={()=>setSignOpen(false)} aria-label="Close"><XCircle/></button></div><div className="signature-identity-preview">{signatureUrl?<img src={signatureUrl} alt={`${data.recipient.full_name} signature`}/>:<strong>{data.recipient.full_name}</strong>}<span>{signatureUrl?"Saved signature image":"Typed signature will be used"}</span></div><dl><div><dt>Signer</dt><dd>{data.recipient.full_name}</dd></div><div><dt>Email</dt><dd>{data.recipient.email}</dd></div><div><dt>Envelope</dt><dd>{data.envelope.envelope_id}</dd></div><div><dt>Placement</dt><dd>{field.signature_page===-1?"Final page":`Page ${field.signature_page}`}</dd></div></dl><label className="confirm-sign"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>I reviewed this document and confirm this signature using my organizational account.</label><div className="modal-actions"><button className="secondary" onClick={()=>setSignOpen(false)}>Cancel</button><button className="primary" disabled={busy||!confirmed} onClick={()=>act("sign")}><CheckCircle2/>Confirm and sign</button></div></section></div>}
  </>}</div>;
}

function VerifyDocument(){
  const [form,setForm]=useState({envelope_id:"",verification_number:"",document_hash:""});const [result,setResult]=useState(null);const [error,setError]=useState("");
  async function verify(event){event.preventDefault();setError("");setResult(null);try{const params=new URLSearchParams({envelope_id:form.envelope_id});if(form.verification_number)params.set("verification_number",form.verification_number);if(form.document_hash)params.set("document_hash",form.document_hash);setResult(await api(`/sign/verify?${params}`));}catch(err){setError(err.message);}}
  return <div className="sign-page narrow-page"><div className="pagehead"><div><span className="eyebrow">Integrity check</span><h1>Verify signed document</h1><p>Confirm an envelope, signer verification number, or SHA-256 document hash.</p></div></div><form className="panel verify-form" onSubmit={verify}><ErrorBox error={error}/><label>Envelope ID<input required placeholder="ENV-2026-000001" value={form.envelope_id} onChange={e=>setForm({...form,envelope_id:e.target.value})}/></label><label>Verification number (optional)<input placeholder="SIG-2026-000001" value={form.verification_number} onChange={e=>setForm({...form,verification_number:e.target.value})}/></label><label>Document SHA-256 hash (optional)<input value={form.document_hash} onChange={e=>setForm({...form,document_hash:e.target.value})}/></label><button className="primary">Verify</button></form>{result&&<section className={`panel verification-result ${result.stored_hash_valid?"valid":"invalid"}`}><ShieldCheck/><h2>{result.stored_hash_valid?"Valid stored document":"Integrity check failed"}</h2><p>{result.envelope_id} · {result.title} · {result.status}</p><div>{result.signers.map(item=><span key={item.full_name}><strong>{item.full_name}</strong>{item.verification_number||item.status}</span>)}</div></section>}</div>;
}
