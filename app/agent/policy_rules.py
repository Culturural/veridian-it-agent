"""
Policy rule implementations for the decision engine.

Each rule function evaluates specific policy conditions and returns
decision recommendations. These are deterministic functions based solely
on the supplied Data Pack policies.

IMPORTANT: These rules do NOT:
- Call external APIs
- Create tickets
- Send emails
- Modify data
- Call LLMs

They only evaluate inputs against policy conditions.

NO INVENTED RULES. Only what the Data Pack explicitly states.

POLICY EVIDENCE IS AUTHORITATIVE:
Rules execute ONLY when corresponding PolicyEvidence is present.
"""

from typing import Optional, List, Tuple
from app.agent.schemas import ExtractedFacts, PolicyEvidence, TicketContext


def password_reset_rule(
    facts: ExtractedFacts,
    policies: List[PolicyEvidence],
    tickets: List[TicketContext],
) -> Optional[Tuple[str, str, List[str], List[str]]]:
    """
    KB-01: Password Reset
    
    Policy: "Employees can reset their own password via the self-service portal 
    at any time. If locked out after 5 failed attempts, contact IT to unlock 
    the account manually. No approval required."
    
    Returns: (decision, reason, actions, sources) or None if not applicable
    """
    # Check if KB-01 is present in policy evidence
    kb01 = next((p for p in policies if p.policy_id == "KB-01"), None)
    if not kb01:
        return None
    
    intent = facts.intent.lower()
    
    # Check if this is a password reset request
    if "password" not in intent and "locked" not in intent and "account" not in intent:
        return None
    
    # Check for lockout scenario (>5 failed attempts)
    failed_attempts = facts.entities.get("failed_attempts")
    issue = str(facts.entities.get("issue", "")).lower()
    
    # Locked after 5 failed attempts → ESCALATE to IT for manual unlock
    if (failed_attempts and failed_attempts > 5) or ("locked" in issue and "5" in issue) or ("locked" in issue and "6" in issue):
        return (
            "ESCALATE",
            "Account is locked after more than 5 failed login attempts. Requires IT to unlock manually per KB-01.",
            ["Contact IT to unlock the account manually"],
            ["KB-01"]
        )
    
    # Normal password reset → RESOLVE
    return (
        "RESOLVE",
        "Employee can reset password using self-service portal per KB-01. No approval required.",
        ["Use the self-service portal to reset your password"],
        ["KB-01"]
    )


def vpn_rule(
    facts: ExtractedFacts,
    policies: List[PolicyEvidence],
    tickets: List[TicketContext],
) -> Optional[Tuple[str, str, List[str], List[str]]]:
    """
    KB-02: VPN Access
    
    Policy: "VPN access is granted automatically to all full-time employees. 
    Contractors require manager approval submitted via the access request form. 
    VPN credentials expire every 90 days and must be renewed by the employee."
    
    Returns: (decision, reason, actions, sources) or None if not applicable
    """
    # Check if KB-02 is present in policy evidence
    kb02 = next((p for p in policies if p.policy_id == "KB-02"), None)
    if not kb02:
        return None
    
    intent = facts.intent.lower()
    
    if "vpn" not in intent:
        return None
    
    issue = str(facts.entities.get("issue", "")).lower()
    employee_type = facts.entities.get("employee_type")
    
    # Expired credentials → RESOLVE with renewal instructions
    if "expired" in issue or "credential" in issue or "stopped working" in issue:
        return (
            "RESOLVE",
            "VPN credentials expire every 90 days and must be renewed by the employee per KB-02.",
            ["Renew your VPN credentials through the VPN portal"],
            ["KB-02"]
        )
    
    # New VPN access request - check employee type
    if employee_type:
        if "contractor" in str(employee_type).lower():
            # Contractor → requires manager approval → ESCALATE
            return (
                "ESCALATE",
                "Contractor VPN access requires manager approval submitted via access request form per KB-02.",
                ["Submit access request form", "Obtain manager approval"],
                ["KB-02"]
            )
        elif "full-time" in str(employee_type).lower() or "full time" in str(employee_type).lower():
            # Full-time employee → automatic → RESOLVE
            return (
                "RESOLVE",
                "VPN access is granted automatically to all full-time employees per KB-02.",
                ["VPN access will be provisioned automatically"],
                ["KB-02"]
            )
    
    # Employee type unknown → FOLLOW_UP
    return (
        "FOLLOW_UP",
        "Need to determine if employee is full-time or contractor to apply KB-02 VPN policy.",
        ["Verify employee type (full-time vs contractor)"],
        ["KB-02"]
    )


def laptop_rule(
    facts: ExtractedFacts,
    policies: List[PolicyEvidence],
    tickets: List[TicketContext],
) -> Optional[Tuple[str, str, List[str], List[str]]]:
    """
    KB-03 + ASSET-01: Laptop Replacement
    
    KB-03: "Laptops are eligible for replacement after 3 years of service, 
    or earlier in case of verified hardware failure. Requests must be raised 
    at least 2 weeks in advance of intended replacement."
    
    ASSET-01: "All company-issued hardware, including laptops and monitors, 
    follows a standard 4-year refresh cycle from date of issue. Early replacement 
    outside this cycle requires Finance sign-off in addition to IT approval."
    
    IMPORTANT: 
    - Reported failure != verified failure
    - >=4 years = normal refresh (within cycle)
    - 3 to <4 years = early replacement (requires Finance sign-off)
    - <3 years = not eligible under normal age criterion
    - Verified failure at ANY age still subject to ASSET-01 if <4 years
    
    Returns: (decision, reason, actions, sources) or None if not applicable
    """
    # Check if KB-03 is present in policy evidence
    kb03 = next((p for p in policies if p.policy_id == "KB-03"), None)
    if not kb03:
        return None
    
    # ASSET-01 is needed for understanding 4-year cycle
    asset01 = next((p for p in policies if p.policy_id == "ASSET-01"), None)
    
    intent = facts.intent.lower()
    
    if "laptop" not in intent and "hardware" not in intent:
        return None
    
    laptop_age_years = facts.entities.get("laptop_age_years") or facts.entities.get("age_years") or facts.entities.get("age") or facts.entities.get("device_age")
    if laptop_age_years is not None:
        try:
            import re
            m = re.search(r'\d+(\.\d+)?', str(laptop_age_years))
            if m:
                laptop_age_years = float(m.group(0))
        except Exception:
            pass

    # Check all entity and intent values to catch symptoms, conditions, issues, problems
    entity_text = " ".join(str(v) for v in facts.entities.values()).lower() + " " + facts.intent.lower()
    verified_failure = facts.entities.get("verified_failure", False)
    
    # Check if this is a replacement request (not just troubleshooting)
    is_replacement = any(word in entity_text for word in ["dead", "won't turn on", "not working", "replacement", "new laptop", "fail", "broken"])
    
    if not is_replacement:
        # Just troubleshooting, not a replacement request
        return None
    
    # Hardware failure mentioned
    if any(word in entity_text for word in ["dead", "won't turn on", "not working", "fail", "broken"]):
        if not verified_failure:
            # Reported but not verified → FOLLOW_UP
            return (
                "FOLLOW_UP",
                "Hardware failure reported but not yet verified. Verification required for early replacement per KB-03.",
                ["Hardware failure must be verified by IT before proceeding with replacement"],
                ["KB-03"]
            )
        else:
            # Verified hardware failure
            # Still need to check ASSET-01 4-year cycle for Finance sign-off requirement
            if asset01 and laptop_age_years < 4:
                # Verified failure but <4 years → still early per ASSET-01 → requires Finance
                sources = ["KB-03", "ASSET-01"]
                return (
                    "ESCALATE",
                    f"Laptop has verified hardware failure and is eligible per KB-03. However, at {laptop_age_years} years, this is early replacement outside the 4-year refresh cycle per ASSET-01 and requires Finance sign-off in addition to IT approval. Request must be raised at least 2 weeks in advance.",
                    ["Requires Finance sign-off in addition to IT approval", "Raise request at least 2 weeks in advance"],
                    sources
                )
            else:
                # Verified failure and either >=4 years or no ASSET-01 → eligible
                return (
                    "RESOLVE",
                    f"Laptop has verified hardware failure. Eligible for replacement per KB-03. Request must be raised at least 2 weeks in advance.",
                    ["Raise replacement request at least 2 weeks in advance"],
                    ["KB-03"]
                )
    
    # Age-based replacement logic (no verified failure)
    if laptop_age_years is None:
        # Age unknown and no verified failure → FOLLOW_UP for age
        sources = ["KB-03", "ASSET-01"] if asset01 else ["KB-03"]
        return (
            "FOLLOW_UP",
            "Need to know laptop age to determine eligibility per KB-03 and ASSET-01.",
            ["Provide the laptop's age in years"],
            sources
        )
    elif laptop_age_years < 3:
        # <3 years → not eligible under KB-03
        sources = ["KB-03", "ASSET-01"] if asset01 else ["KB-03"]
        return (
            "ESCALATE",
            f"Laptop is {laptop_age_years} years old. Not eligible for replacement under the normal 3-year criterion per KB-03. Early replacement requires Finance sign-off and IT approval per ASSET-01." if asset01 else f"Laptop is {laptop_age_years} years old. Not eligible for replacement under the normal 3-year criterion per KB-03.",
            ["Requires Finance sign-off in addition to IT approval"] if asset01 else ["Not eligible under standard policy"],
            sources
        )
    elif laptop_age_years < 4:
        # 3 to <4 years → eligible per KB-03 but early per ASSET-01 → requires Finance
        sources = ["KB-03", "ASSET-01"] if asset01 else ["KB-03"]
        return (
            "ESCALATE",
            f"Laptop is {laptop_age_years} years old. Eligible per KB-03 (>3 years), but this is early replacement outside the 4-year refresh cycle per ASSET-01 and requires Finance sign-off in addition to IT approval. Request must be raised at least 2 weeks in advance." if asset01 else f"Laptop is {laptop_age_years} years old. Eligible per KB-03. Request must be raised at least 2 weeks in advance.",
            ["Requires Finance sign-off in addition to IT approval", "Raise request at least 2 weeks in advance"] if asset01 else ["Raise request at least 2 weeks in advance"],
            sources
        )
    else:
        # >=4 years → normal refresh cycle → RESOLVE
        sources = ["KB-03", "ASSET-01"] if asset01 else ["KB-03"]
        return (
            "RESOLVE",
            f"Laptop is {laptop_age_years} years old, within the standard 4-year refresh cycle per ASSET-01 and eligible per KB-03. Request must be raised at least 2 weeks in advance." if asset01 else f"Laptop is {laptop_age_years} years old. Eligible per KB-03. Request must be raised at least 2 weeks in advance.",
            ["Raise replacement request at least 2 weeks in advance"],
            sources
        )


def software_rule(
    facts: ExtractedFacts,
    policies: List[PolicyEvidence],
    tickets: List[TicketContext],
) -> Optional[Tuple[str, str, List[str], List[str]]]:
    """
    KB-04: Software Installation Requests
    
    Policy: "Standard software (listed in the approved catalog) can be self-installed. 
    Non-catalog software requires IT Security review, which takes 3–5 business days."
    
    Returns: (decision, reason, actions, sources) or None if not applicable
    """
    # Check if KB-04 is present in policy evidence
    kb04 = next((p for p in policies if p.policy_id == "KB-04"), None)
    if not kb04:
        return None
    
    intent = facts.intent.lower()
    
    if "software" not in intent and "install" not in intent and "extension" not in intent:
        return None
    
    software_name = facts.entities.get("software_name") or facts.entities.get("software")
    in_catalog = facts.entities.get("in_catalog")
    
    # Missing software name → FOLLOW_UP
    if not software_name:
        return (
            "FOLLOW_UP",
            "Need to know which software/tool to determine if it's in the approved catalog per KB-04.",
            ["Specify the software name or tool"],
            ["KB-04"]
        )
    
    # Catalog status must be known - NEVER assume
    if in_catalog is None:
        # Catalog status unknown → FOLLOW_UP
        return (
            "FOLLOW_UP",
            f"Need to verify if '{software_name}' is in the approved software catalog per KB-04.",
            ["Check if software is in the approved catalog"],
            ["KB-04"]
        )
    
    # Catalog status known
    if in_catalog:
        # In catalog → self-install → RESOLVE
        return (
            "RESOLVE",
            f"Software '{software_name}' is in the approved catalog. Can be self-installed per KB-04.",
            ["Self-install the software from the approved catalog"],
            ["KB-04"]
        )
    else:
        # Not in catalog → Security review → ESCALATE
        return (
            "ESCALATE",
            f"Software '{software_name}' is not in the approved catalog. Requires IT Security review per KB-04, which takes 3–5 business days.",
            ["Submit for IT Security review (3–5 business days)"],
            ["KB-04"]
        )


def printer_rule(
    facts: ExtractedFacts,
    policies: List[PolicyEvidence],
    tickets: List[TicketContext],
) -> Optional[Tuple[str, str, List[str], List[str]]]:
    """
    KB-05: Printer Troubleshooting
    
    Policy: "For printer issues, first check the printer queue and restart 
    the print spooler. If the issue persists after restart, log a ticket 
    with the printer's asset tag."
    
    Returns: (decision, reason, actions, sources) or None if not applicable
    """
    # Check if KB-05 is present in policy evidence
    kb05 = next((p for p in policies if p.policy_id == "KB-05"), None)
    if not kb05:
        return None
    
    intent = facts.intent.lower()
    
    if "printer" not in intent and "print" not in intent:
        return None
    
    troubleshooting_attempted = facts.entities.get("troubleshooting_attempted", False)
    asset_tag = facts.entities.get("asset_tag")
    
    # Troubleshooting not yet attempted → RESOLVE with instructions
    if not troubleshooting_attempted:
        return (
            "RESOLVE",
            "For printer issues, first check the printer queue and restart the print spooler per KB-05.",
            ["Check the printer queue", "Restart the print spooler"],
            ["KB-05"]
        )
    
    # Troubleshooting attempted and issue persists
    if asset_tag:
        # Has asset tag → ESCALATE to log ticket
        return (
            "ESCALATE",
            f"Troubleshooting attempted. Issue persists. Log a ticket with printer asset tag '{asset_tag}' per KB-05.",
            ["Log a ticket with the printer's asset tag"],
            ["KB-05"]
        )
    else:
        # Missing asset tag → FOLLOW_UP
        return (
            "FOLLOW_UP",
            "Troubleshooting attempted. Issue persists. Need the printer's asset tag to log a ticket per KB-05.",
            ["Obtain the printer's asset tag"],
            ["KB-05"]
        )


def mailbox_rule(
    facts: ExtractedFacts,
    policies: List[PolicyEvidence],
    tickets: List[TicketContext],
) -> Optional[Tuple[str, str, List[str], List[str]]]:
    """
    KB-06: Email Mailbox Quota
    
    Policy: "Default mailbox quota is 25GB. Employees nearing quota should 
    archive old mail. Quota increases beyond 25GB require manager approval 
    and are capped at 50GB."
    
    Returns: (decision, reason, actions, sources) or None if not applicable
    """
    # Check if KB-06 is present in policy evidence
    kb06 = next((p for p in policies if p.policy_id == "KB-06"), None)
    if not kb06:
        return None
    
    intent = facts.intent.lower()
    
    # Exclude security incidents (phishing, malware, unauthorized access)
    if "phishing" in intent or "security" in intent or "malware" in intent or "suspicious" in intent:
        return None
    
    if "mailbox" not in intent and "quota" not in intent:
        issue = str(facts.entities.get("issue", "")).lower()
        if not any(k in issue for k in ["quota", "storage", "full", "space", "limit", "gb", "archive", "capacity"]):
            return None
    
    issue = str(facts.entities.get("issue", "")).lower()
    requested_quota_gb = facts.entities.get("requested_quota_gb")
    current_quota_gb = facts.entities.get("current_quota_gb", 25)  # Default is 25GB
    
    # Mailbox full / nearing full → archive old mail → RESOLVE
    if "full" in issue or "nearing" in issue or "can't send" in issue:
        return (
            "RESOLVE",
            "Default mailbox quota is 25GB. Employees nearing quota should archive old mail per KB-06.",
            ["Archive old mail to free up space"],
            ["KB-06"]
        )
    
    # Quota increase request
    if requested_quota_gb:
        if requested_quota_gb > 50:
            # Beyond 50GB cap → ESCALATE
            return (
                "ESCALATE",
                f"Requested quota of {requested_quota_gb}GB exceeds the 50GB maximum per KB-06. Quota increases beyond 25GB require manager approval and are capped at 50GB.",
                ["Explain that maximum quota is 50GB", "Consider archiving old mail instead"],
                ["KB-06"]
            )
        elif requested_quota_gb > 25:
            # 26-50GB → requires manager approval → ESCALATE
            return (
                "ESCALATE",
                f"Quota increase from {current_quota_gb}GB to {requested_quota_gb}GB requires manager approval per KB-06. Quota increases beyond 25GB require manager approval and are capped at 50GB.",
                ["Obtain manager approval for quota increase"],
                ["KB-06"]
            )
        else:
            # <=25GB (within default) → RESOLVE
            return (
                "RESOLVE",
                f"Requested quota of {requested_quota_gb}GB is within the default 25GB quota per KB-06.",
                ["No approval needed for quota within default 25GB"],
                ["KB-06"]
            )
    
    # General mailbox issue without specific quota request
    return (
        "RESOLVE",
        "Default mailbox quota is 25GB. Archive old mail if nearing quota. Quota increases beyond 25GB require manager approval per KB-06.",
        ["Archive old mail", "Request quota increase with manager approval if needed"],
        ["KB-06"]
    )


def guest_wifi_rule(
    facts: ExtractedFacts,
    policies: List[PolicyEvidence],
    tickets: List[TicketContext],
) -> Optional[Tuple[str, str, List[str], List[str]]]:
    """
    KB-07: Guest Wi-Fi Access
    
    Policy: "Guest Wi-Fi credentials are valid for 24 hours and can be 
    generated by any employee from the front-desk kiosk. No IT ticket required."
    
    Returns: (decision, reason, actions, sources) or None if not applicable
    """
    # Check if KB-07 is present in policy evidence
    kb07 = next((p for p in policies if p.policy_id == "KB-07"), None)
    if not kb07:
        return None
    
    intent = facts.intent.lower()
    
    if "guest" not in intent and "wifi" not in intent and "wi-fi" not in intent:
        return None
    
    duration_hours = facts.entities.get("duration_hours", 24)
    
    # Standard guest WiFi (≤24 hours) → RESOLVE
    if duration_hours <= 24:
        return (
            "RESOLVE",
            "Guest Wi-Fi credentials are valid for 24 hours and can be generated by any employee from the front-desk kiosk per KB-07. No IT ticket required.",
            ["Generate guest WiFi credentials from the front-desk kiosk"],
            ["KB-07"]
        )
    
    # Request beyond 24 hours → unsupported by policy → ESCALATE
    return (
        "ESCALATE",
        f"Guest WiFi request for {duration_hours} hours exceeds the standard 24-hour validity per KB-07. Extended access not covered by supplied policy.",
        ["Standard guest WiFi is 24 hours only", "Policy does not provide extension procedure"],
        ["KB-07"]
    )


def expense_rule(
    facts: ExtractedFacts,
    policies: List[PolicyEvidence],
    tickets: List[TicketContext],
) -> Optional[Tuple[str, str, List[str], List[str]]]:
    """
    KB-08: Expense Software Access
    
    Policy: "Access to the expense management tool is granted by Finance, not IT. 
    IT can only assist with login/technical issues once an account already exists."
    
    Returns: (decision, reason, actions, sources) or None if not applicable
    """
    # Check if KB-08 is present in policy evidence
    kb08 = next((p for p in policies if p.policy_id == "KB-08"), None)
    if not kb08:
        return None
    
    intent = facts.intent.lower()
    
    if "expense" not in intent:
        return None
    
    issue = str(facts.entities.get("issue", "")).lower()
    account_exists = facts.entities.get("account_exists")
    
    # Account existence must be known for login/technical issues
    if "login" in issue or "credentials" in issue or "invalid" in issue or "technical" in issue:
        if account_exists is None:
            # Don't know if account exists → FOLLOW_UP
            return (
                "FOLLOW_UP",
                "Need to verify if expense tool account exists. IT can only assist with login/technical issues once an account already exists per KB-08.",
                ["Verify if account exists in expense tool"],
                ["KB-08"]
            )
        elif account_exists:
            # Account exists → IT can help → RESOLVE
            return (
                "RESOLVE",
                "IT can assist with expense tool login/technical issues once an account already exists per KB-08.",
                ["Reset password or troubleshoot login issue"],
                ["KB-08"]
            )
        else:
            # Account doesn't exist → Finance grants access → ESCALATE
            return (
                "ESCALATE",
                "No existing account found. Access to the expense management tool is granted by Finance, not IT, per KB-08.",
                ["Contact Finance to request expense tool access"],
                ["KB-08"]
            )
    
    # Access request (new account) → Finance grants access → ESCALATE
    if "access" in issue or "need" in issue:
        return (
            "ESCALATE",
            "Access to the expense management tool is granted by Finance, not IT, per KB-08. IT can only assist with login/technical issues once an account already exists.",
            ["Contact Finance to request expense tool access"],
            ["KB-08"]
        )
    
    # General expense tool issue - need more info
    return (
        "FOLLOW_UP",
        "Need to clarify the expense tool issue. IT can assist with login/technical issues per KB-08. For new access, contact Finance.",
        ["Clarify if this is a login issue or access request"],
        ["KB-08"]
    )


def security_rule(
    facts: ExtractedFacts,
    policies: List[PolicyEvidence],
    tickets: List[TicketContext],
) -> Optional[Tuple[str, str, List[str], List[str]]]:
    """
    KB-09: Security Incident Reporting
    
    Policy: "Any suspected phishing email, malware, or unauthorized access 
    attempt must be reported to security@veridian-corp.example immediately 
    and should not be forwarded to other employees."
    
    ONLY applies to supplied categories:
    - suspected phishing
    - malware
    - unauthorized access attempt
    
    Returns: (decision, reason, actions, sources) or None if not applicable
    """
    # Check if KB-09 is present in policy evidence
    kb09 = next((p for p in policies if p.policy_id == "KB-09"), None)
    if not kb09:
        return None
    
    intent = facts.intent.lower()
    issue = str(facts.entities.get("issue", "")).lower()
    
    # Check if this matches the supplied categories ONLY
    is_phishing = "phishing" in intent or "phishing" in issue
    is_malware = "malware" in intent or "malware" in issue
    is_unauthorized = "unauthorized" in intent or "unauthorized access" in issue
    
    if not (is_phishing or is_malware or is_unauthorized):
        # Not one of the supplied categories
        return None
    
    user_action = str(facts.entities.get("user_action", "")).lower()
    
    # Check if user plans unsafe action (forwarding to teammates)
    unsafe_action = "forward" in user_action or "forwarding" in user_action
    
    # ALL supplied security incidents → ESCALATE to security@veridian-corp.example
    if unsafe_action:
        return (
            "ESCALATE",
            "Any suspected phishing email, malware, or unauthorized access attempt must be reported to security@veridian-corp.example immediately per KB-09. DO NOT forward to other employees.",
            ["Report immediately to security@veridian-corp.example", "Do not forward the message to other employees"],
            ["KB-09"]
        )
    else:
        return (
            "ESCALATE",
            "Any suspected phishing email, malware, or unauthorized access attempt must be reported to security@veridian-corp.example immediately per KB-09.",
            ["Report immediately to security@veridian-corp.example", "Do not forward the message to other employees"],
            ["KB-09"]
        )


def wfh_rule(
    facts: ExtractedFacts,
    policies: List[PolicyEvidence],
    tickets: List[TicketContext],
) -> Optional[Tuple[str, str, List[str], List[str]]]:
    """
    KB-10: Work-From-Home Equipment
    
    Policy: "Employees working remotely more than 3 days/week are eligible 
    for a one-time home office equipment allowance (chair, monitor). Requires 
    manager sign-off and Finance processing — IT only handles the equipment 
    shipping request once approved."
    
    Returns: (decision, reason, actions, sources) or None if not applicable
    """
    # Check if KB-10 is present in policy evidence
    kb10 = next((p for p in policies if p.policy_id == "KB-10"), None)
    if not kb10:
        return None
    
    intent = facts.intent.lower()
    
    if "wfh" not in intent and "work from home" not in intent and "remote" not in intent and "home office" not in intent:
        return None
    
    remote_days_per_week = facts.entities.get("remote_days_per_week")
    
    # Missing remote days info → FOLLOW_UP
    if remote_days_per_week is None:
        return (
            "FOLLOW_UP",
            "Need to know how many days per week employee works remotely to determine eligibility per KB-10.",
            ["Verify number of remote work days per week"],
            ["KB-10"]
        )
    
    # Not eligible (≤3 days/week) → ESCALATE
    if remote_days_per_week <= 3:
        return (
            "ESCALATE",
            f"Employee works remotely {remote_days_per_week} days/week. Eligibility requires more than 3 days/week per KB-10. Not eligible under supplied policy.",
            ["Explain eligibility requires more than 3 days/week remote work"],
            ["KB-10"]
        )
    
    # Eligible (>3 days/week) → requires manager sign-off and Finance → ESCALATE
    return (
        "ESCALATE",
        f"Employee works remotely {remote_days_per_week} days/week and is eligible for one-time home office equipment allowance (chair, monitor) per KB-10. Requires manager sign-off and Finance processing. IT only handles equipment shipping once approved.",
        ["Obtain manager sign-off", "Submit to Finance for processing", "IT will handle shipping once approved"],
        ["KB-10"]
    )
