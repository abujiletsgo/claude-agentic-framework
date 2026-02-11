"""Test file with intentional code duplication for review system testing."""


def process_user_data(users):
    """Process user data with validation and transformation."""
    result = []
    for user in users:
        if not user:
            continue
        if not isinstance(user, dict):
            continue
        name = user.get("name", "")
        email = user.get("email", "")
        age = user.get("age", 0)
        if not name or not email:
            continue
        if age < 0 or age > 150:
            continue
        processed = {
            "full_name": name.strip().title(),
            "email_address": email.strip().lower(),
            "user_age": int(age),
            "is_adult": age >= 18,
            "category": "senior" if age >= 65 else "adult" if age >= 18 else "minor",
        }
        result.append(processed)
    return result


def process_customer_data(customers):
    """Process customer data with validation and transformation."""
    result = []
    for customer in customers:
        if not customer:
            continue
        if not isinstance(customer, dict):
            continue
        name = customer.get("name", "")
        email = customer.get("email", "")
        age = customer.get("age", 0)
        if not name or not email:
            continue
        if age < 0 or age > 150:
            continue
        processed = {
            "full_name": name.strip().title(),
            "email_address": email.strip().lower(),
            "user_age": int(age),
            "is_adult": age >= 18,
            "category": "senior" if age >= 65 else "adult" if age >= 18 else "minor",
        }
        result.append(processed)
    return result


def process_employee_data(employees):
    """Process employee data with validation and transformation."""
    result = []
    for employee in employees:
        if not employee:
            continue
        if not isinstance(employee, dict):
            continue
        name = employee.get("name", "")
        email = employee.get("email", "")
        age = employee.get("age", 0)
        if not name or not email:
            continue
        if age < 0 or age > 150:
            continue
        processed = {
            "full_name": name.strip().title(),
            "email_address": email.strip().lower(),
            "user_age": int(age),
            "is_adult": age >= 18,
            "category": "senior" if age >= 65 else "adult" if age >= 18 else "minor",
        }
        result.append(processed)
    return result
