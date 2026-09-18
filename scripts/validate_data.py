"""
Data validation script for Veridian IT Service Agent.

Validates the structure and integrity of the ground truth data files:
- data/policies.json
- data/requests.json
- data/tickets.json

This script does not require external services (OpenAI, ChromaDB, etc.)
and can be run independently to verify data integrity.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json_file(file_path: Path) -> Tuple[bool, Any, str]:
    """
    Load and parse a JSON file.
    
    Returns:
        Tuple of (success, data, error_message)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, data, ""
    except FileNotFoundError:
        return False, None, f"File not found: {file_path}"
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON in {file_path}: {e}"
    except Exception as e:
        return False, None, f"Error loading {file_path}: {e}"


def validate_policies(policies: List[Dict[str, Any]]) -> List[str]:
    """Validate policy records."""
    errors = []
    
    # Expected count
    if len(policies) != 11:
        errors.append(f"Expected 11 policies, found {len(policies)}")
    
    # Expected IDs
    expected_ids = [
        "KB-01", "KB-02", "KB-03", "KB-04", "KB-05",
        "KB-06", "KB-07", "KB-08", "KB-09", "KB-10",
        "ASSET-01"
    ]
    
    found_ids = [p.get("id") for p in policies]
    
    # Check for missing IDs
    missing = set(expected_ids) - set(found_ids)
    if missing:
        errors.append(f"Missing policy IDs: {sorted(missing)}")
    
    # Check for unexpected IDs
    unexpected = set(found_ids) - set(expected_ids)
    if unexpected:
        errors.append(f"Unexpected policy IDs: {sorted(unexpected)}")
    
    # Check for duplicates
    if len(found_ids) != len(set(found_ids)):
        duplicates = [id for id in found_ids if found_ids.count(id) > 1]
        errors.append(f"Duplicate policy IDs: {set(duplicates)}")
    
    # Validate required fields
    required_fields = ["id", "title", "category", "content", "source_type"]
    for i, policy in enumerate(policies):
        for field in required_fields:
            if field not in policy:
                errors.append(f"Policy index {i} (ID: {policy.get('id', 'UNKNOWN')}) missing field: {field}")
            elif not policy[field]:
                errors.append(f"Policy {policy.get('id', 'UNKNOWN')} has empty field: {field}")
    
    # Validate source_type values
    valid_source_types = ["knowledge_base", "policy_extract"]
    for policy in policies:
        source_type = policy.get("source_type")
        if source_type and source_type not in valid_source_types:
            errors.append(f"Policy {policy.get('id')} has invalid source_type: {source_type}")
    
    return errors


def validate_requests(requests: List[Dict[str, Any]]) -> List[str]:
    """Validate employee request records."""
    errors = []
    
    # Expected count
    if len(requests) != 15:
        errors.append(f"Expected 15 requests, found {len(requests)}")
    
    # Expected IDs
    expected_ids = [f"REQ-{i:02d}" for i in range(1, 16)]
    
    found_ids = [r.get("request_id") for r in requests]
    
    # Check for missing IDs
    missing = set(expected_ids) - set(found_ids)
    if missing:
        errors.append(f"Missing request IDs: {sorted(missing)}")
    
    # Check for unexpected IDs
    unexpected = set(found_ids) - set(expected_ids)
    if unexpected:
        errors.append(f"Unexpected request IDs: {sorted(unexpected)}")
    
    # Check for duplicates
    if len(found_ids) != len(set(found_ids)):
        duplicates = [id for id in found_ids if found_ids.count(id) > 1]
        errors.append(f"Duplicate request IDs: {set(duplicates)}")
    
    # Validate required fields
    required_fields = ["request_id", "employee", "email", "date_opened", "request", "initial_action_taken"]
    for i, request in enumerate(requests):
        for field in required_fields:
            if field not in request:
                errors.append(f"Request index {i} (ID: {request.get('request_id', 'UNKNOWN')}) missing field: {field}")
            elif not request[field]:
                errors.append(f"Request {request.get('request_id', 'UNKNOWN')} has empty field: {field}")
    
    # Validate email format (basic check)
    for request in requests:
        email = request.get("email", "")
        if email and "@" not in email:
            errors.append(f"Request {request.get('request_id')} has invalid email format: {email}")
    
    return errors


def validate_tickets(tickets: List[Dict[str, Any]]) -> List[str]:
    """Validate ticket records."""
    errors = []
    
    # Expected count
    if len(tickets) != 10:
        errors.append(f"Expected 10 tickets, found {len(tickets)}")
    
    # Expected IDs
    expected_ids = [f"TK-{i}" for i in range(1042, 1052)]
    
    found_ids = [t.get("ticket_id") for t in tickets]
    
    # Check for missing IDs
    missing = set(expected_ids) - set(found_ids)
    if missing:
        errors.append(f"Missing ticket IDs: {sorted(missing)}")
    
    # Check for unexpected IDs
    unexpected = set(found_ids) - set(expected_ids)
    if unexpected:
        errors.append(f"Unexpected ticket IDs: {sorted(unexpected)}")
    
    # Check for duplicates
    if len(found_ids) != len(set(found_ids)):
        duplicates = [id for id in found_ids if found_ids.count(id) > 1]
        errors.append(f"Duplicate ticket IDs: {set(duplicates)}")
    
    # Validate required fields
    required_fields = ["ticket_id", "employee", "issue_summary", "status"]
    for i, ticket in enumerate(tickets):
        for field in required_fields:
            if field not in ticket:
                errors.append(f"Ticket index {i} (ID: {ticket.get('ticket_id', 'UNKNOWN')}) missing field: {field}")
            elif not ticket[field]:
                errors.append(f"Ticket {ticket.get('ticket_id', 'UNKNOWN')} has empty field: {field}")
    
    return errors


def main():
    """Main validation function."""
    print("Veridian IT Service Agent - Data Validation")
    print("=" * 60)
    
    # Determine data directory path
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    data_dir = project_root / "data"
    
    all_errors = []
    
    # Validate policies
    print("\n1. Validating policies.json...")
    success, policies, error = load_json_file(data_dir / "policies.json")
    if not success:
        all_errors.append(error)
        print(f"   ✗ {error}")
    else:
        policy_errors = validate_policies(policies)
        if policy_errors:
            all_errors.extend(policy_errors)
            for err in policy_errors:
                print(f"   ✗ {err}")
        else:
            print(f"   ✓ Valid: {len(policies)} policies")
    
    # Validate requests
    print("\n2. Validating requests.json...")
    success, requests, error = load_json_file(data_dir / "requests.json")
    if not success:
        all_errors.append(error)
        print(f"   ✗ {error}")
    else:
        request_errors = validate_requests(requests)
        if request_errors:
            all_errors.extend(request_errors)
            for err in request_errors:
                print(f"   ✗ {err}")
        else:
            print(f"   ✓ Valid: {len(requests)} requests")
    
    # Validate tickets
    print("\n3. Validating tickets.json...")
    success, tickets, error = load_json_file(data_dir / "tickets.json")
    if not success:
        all_errors.append(error)
        print(f"   ✗ {error}")
    else:
        ticket_errors = validate_tickets(tickets)
        if ticket_errors:
            all_errors.extend(ticket_errors)
            for err in ticket_errors:
                print(f"   ✗ {err}")
        else:
            print(f"   ✓ Valid: {len(tickets)} tickets")
    
    # Summary
    print("\n" + "=" * 60)
    if all_errors:
        print(f"VALIDATION FAILED: {len(all_errors)} error(s) found")
        sys.exit(1)
    else:
        print("VALIDATION PASSED: All data files are valid")
        print("\nSummary:")
        print(f"  - Policies: 11")
        print(f"  - Requests: 15")
        print(f"  - Tickets: 10")
        print(f"  - Total records: 36")
        sys.exit(0)


if __name__ == "__main__":
    main()
