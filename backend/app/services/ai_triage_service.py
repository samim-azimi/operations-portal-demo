import json,re
from pydantic import BaseModel,Field,field_validator
from app.config import settings

CATEGORIES={"Network","Email","Printer","Hardware","Software","Account","Security","Other"}
PRIORITIES={"Low","Medium","High","Critical"}
class TriageResult(BaseModel):
    category:str; priority:str; summary:str; possible_root_cause:str; troubleshooting_steps:list[str]=Field(min_length=1)
    recommended_team:str; needs_human_approval:bool; suggested_user_reply:str; confidence_score:float=Field(ge=0,le=1)
    @field_validator("category")
    @classmethod
    def category_valid(cls,v):
        if v not in CATEGORIES: raise ValueError("invalid category")
        return v
    @field_validator("priority")
    @classmethod
    def priority_valid(cls,v):
        if v not in PRIORITIES: raise ValueError("invalid priority")
        return v

class AITriageService:
    def build_prompt(self,ticket,similar):
        knowledge="\n".join(f"- {x['title']}: {x['solution']}" for x in similar) or "No matching articles."
        return f"""You are a cautious IT helpdesk triage assistant. Return ONLY a JSON object with keys category, priority, summary, possible_root_cause, troubleshooting_steps, recommended_team, needs_human_approval, suggested_user_reply, confidence_score.
Allowed categories: {sorted(CATEGORIES)}. Allowed priorities: {sorted(PRIORITIES)}.
AI must never close a ticket or claim an email was sent. Security, Account, High and Critical work needs human approval.
Ticket: {ticket.title}
Description: {ticket.description}
Urgency: {ticket.urgency}
Department: {ticket.department}
Location: {ticket.location}
Relevant knowledge:
{knowledge}"""
    def fallback(self,ticket):
        text=f"{ticket.title} {ticket.description}".lower()
        rules=[("Security",["virus","phishing","malware","security","ransomware"]),("Printer",["printer","toner","scan"]),("Account",["password","login","account","locked out"]),("Email",["outlook","email","m365","microsoft 365","teams"]),("Network",["internet","wi-fi","wifi","network","vpn"]),("Hardware",["laptop","overheat","screen","keyboard","disk"]),("Software",["software","application","app","install"])]
        category="Other"; matched=[]
        for name,words in rules:
            matched=[w for w in words if w in text]
            if matched: category=name; break
        many=bool(re.search(r"many users|everyone|whole (office|team)|company.?wide|all users",text))
        if ticket.urgency=="Critical" or (many and ticket.urgency in {"High","Critical"}): priority="Critical"
        elif ticket.urgency=="High" or many or category=="Security": priority="High"
        elif ticket.urgency=="Low": priority="Low"
        else: priority="Medium"
        teams={"Network":"Network Team","Email":"M365 Admin","Security":"Security Team","Account":"IT Support"}
        team=teams.get(category,"IT Support")
        approval=category in {"Security","Account"} or priority in {"High","Critical"}
        steps={
          "Network":["Confirm whether other devices are affected","Restart the network adapter or VPN client","Capture connection errors and test connectivity"],
          "Email":["Check Microsoft 365 service status","Restart Outlook and verify connectivity","Recreate the profile only after preserving local data"],
          "Printer":["Check power, paper, toner, and displayed errors","Clear the print queue and retry","Verify the correct printer and driver"],
          "Account":["Confirm the exact sign-in error","Check account lock and license status","Use the approved identity verification and reset process"],
          "Security":["Disconnect the affected device from the network if compromise is suspected","Preserve evidence and record indicators","Escalate immediately to the Security Team"],
          "Hardware":["Record hardware symptoms and recent changes","Run vendor diagnostics","Back up data before repair or replacement"],
          "Software":["Restart the application and capture the error","Check version, licensing, and recent updates","Repair or reinstall with user approval"],
          "Other":["Reproduce the issue and capture the exact error","Check recent changes and affected scope","Escalate with diagnostic logs if unresolved"]}[category]
        return TriageResult(category=category,priority=priority,summary=ticket.title[:160],possible_root_cause=f"Likely {category.lower()} configuration, service, or endpoint issue based on the reported symptoms.",troubleshooting_steps=steps,recommended_team=team,needs_human_approval=approval,suggested_user_reply=f"Dear {ticket.full_name}, thank you for reporting this issue. We have received your request and our IT team is reviewing it. Based on the details provided, it appears related to {category}. We will update you after the next action is completed.",confidence_score=0.82 if matched else 0.55)
    def triage(self,ticket,similar):
        if not settings.openai_api_key:
            return self.fallback(ticket),"rules"
        try:
            from openai import OpenAI
            response=OpenAI(api_key=settings.openai_api_key).chat.completions.create(model=settings.openai_model,messages=[{"role":"user","content":self.build_prompt(ticket,similar)}],response_format={"type":"json_object"},temperature=0.1)
            result=TriageResult.model_validate(json.loads(response.choices[0].message.content))
            result.needs_human_approval=result.needs_human_approval or result.category in {"Security","Account"} or result.priority in {"High","Critical"}
            return result,"openai"
        except Exception:
            return self.fallback(ticket),"rules-fallback"
