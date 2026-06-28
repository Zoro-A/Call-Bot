"""
In-memory appointment store for the Dentist Bot demo.
Replace the storage backend with a real calendar API (Google Calendar, Calendly, etc.) for production.
"""

import random
import string
from datetime import datetime, time
from typing import Annotated

from livekit.agents import llm

# --- Mock data store ---

_appointments: dict[str, dict] = {}

_AVAILABLE_SLOTS = [
    "9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM",
    "11:00 AM", "11:30 AM", "12:00 PM",
    "2:00 PM", "2:30 PM", "3:00 PM", "3:30 PM",
    "4:00 PM", "4:30 PM", "5:00 PM",
]

_CLINIC_INFO = {
    "hours": (
        "Monday–Thursday: 9:00 AM – 6:00 PM\n"
        "Friday: 9:00 AM – 5:00 PM\n"
        "Saturday: 10:00 AM – 3:00 PM\n"
        "Sunday: Closed"
    ),
    "location": "123 Main Street, DHA Phase 6, Karachi. Free parking in the building basement.",
    "services": (
        "Teeth Cleaning (PKR 3,000), Dental Fillings (PKR 4,000), "
        "Teeth Whitening (PKR 15,000), Root Canal (PKR 12,000), "
        "Tooth Extraction (PKR 3,500), Dental Implant Consultation (PKR 2,000), "
        "Braces / Orthodontics Consultation (PKR 2,000), Emergency Care (PKR 2,000)."
    ),
    "insurance": (
        "We accept Jubilee Insurance, EFU Health, Allianz Care, and State Life Insurance. "
        "Cash and card payments are also welcome."
    ),
    "doctors": (
        "Dr. Ayesha Khan — General & Cosmetic Dentistry, Orthodontics. "
        "Dr. Zain Malik — Root Canal & Restorative Dentistry."
    ),
    "emergency": (
        "For dental emergencies during clinic hours, call us directly. "
        "We accommodate same-day emergency appointments."
    ),
}


def _generate_confirmation() -> str:
    return "BSD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


# --- Tool functions ---

@llm.function_tool()
async def check_availability(
    date: Annotated[str, "The date to check, e.g. 'Monday', 'July 5th', or '2026-07-05'"],
) -> str:
    """Check available appointment slots for a given date at the clinic."""
    # In a real integration this would query a calendar API.
    # For the demo we return a fixed set of slots.
    slots = _AVAILABLE_SLOTS.copy()
    # Simulate some slots being taken
    taken = random.sample(slots, k=min(4, len(slots)))
    available = [s for s in slots if s not in taken]
    if not available:
        return f"Unfortunately there are no available slots on {date}. Would you like to try another date?"
    slots_str = ", ".join(available)
    return f"Available slots on {date}: {slots_str}. Which time works best for you?"


@llm.function_tool()
async def book_appointment(
    patient_name: Annotated[str, "Full name of the patient"],
    phone: Annotated[str, "Patient's contact phone number"],
    date: Annotated[str, "Appointment date, e.g. 'Monday July 7th' or '2026-07-07'"],
    time_slot: Annotated[str, "Appointment time, e.g. '10:00 AM'"],
    service: Annotated[str, "The dental service requested, e.g. 'Teeth Cleaning'"],
) -> str:
    """Book an appointment for a patient at the clinic."""
    confirmation = _generate_confirmation()
    _appointments[confirmation] = {
        "patient_name": patient_name,
        "phone": phone,
        "date": date,
        "time": time_slot,
        "service": service,
        "status": "confirmed",
    }
    return (
        f"Done! I've booked a {service} appointment for {patient_name} "
        f"on {date} at {time_slot}. "
        f"Your confirmation number is {confirmation}. "
        f"Please arrive 10 minutes early if you're a new patient, "
        f"and bring any previous dental records if you have them. "
        f"Our cancellation policy requires at least 4 hours notice."
    )


@llm.function_tool()
async def cancel_appointment(
    confirmation_number: Annotated[str, "The appointment confirmation number, e.g. BSD-ABC123"],
) -> str:
    """Cancel an existing appointment using the confirmation number."""
    confirmation_number = confirmation_number.upper().strip()
    appt = _appointments.get(confirmation_number)
    if not appt:
        return (
            f"I couldn't find an appointment with confirmation number {confirmation_number}. "
            "Please double-check the number, or I can help you book a new appointment."
        )
    if appt["status"] == "cancelled":
        return f"Appointment {confirmation_number} was already cancelled."

    appt["status"] = "cancelled"
    return (
        f"I've successfully cancelled the {appt['service']} appointment for {appt['patient_name']} "
        f"on {appt['date']} at {appt['time']}. "
        f"Confirmation number {confirmation_number} is now void. "
        "Is there anything else I can help you with?"
    )


@llm.function_tool()
async def reschedule_appointment(
    confirmation_number: Annotated[str, "The existing appointment confirmation number"],
    new_date: Annotated[str, "The new date for the appointment"],
    new_time: Annotated[str, "The new time for the appointment, e.g. '2:30 PM'"],
) -> str:
    """Reschedule an existing appointment to a new date and time."""
    confirmation_number = confirmation_number.upper().strip()
    appt = _appointments.get(confirmation_number)
    if not appt:
        return (
            f"I couldn't find an appointment with confirmation number {confirmation_number}. "
            "Please double-check the number."
        )
    if appt["status"] == "cancelled":
        return (
            f"Appointment {confirmation_number} was already cancelled and cannot be rescheduled. "
            "Would you like to book a new appointment?"
        )

    old_date = appt["date"]
    old_time = appt["time"]
    appt["date"] = new_date
    appt["time"] = new_time

    new_confirmation = _generate_confirmation()
    _appointments[new_confirmation] = {**appt}
    appt["status"] = "rescheduled"

    return (
        f"Done! I've rescheduled {appt['patient_name']}'s {appt['service']} "
        f"from {old_date} at {old_time} "
        f"to {new_date} at {new_time}. "
        f"Your new confirmation number is {new_confirmation}."
    )


@llm.function_tool()
async def get_clinic_info(
    topic: Annotated[
        str,
        "The topic to get information about. Options: hours, location, services, insurance, doctors, emergency"
    ],
) -> str:
    """Get information about the dental clinic such as hours, location, services, or insurance."""
    topic_key = topic.lower().strip()
    for key in _CLINIC_INFO:
        if key in topic_key or topic_key in key:
            return _CLINIC_INFO[key]
    # Fallback: return all info
    all_info = "\n\n".join(f"{k.title()}: {v}" for k, v in _CLINIC_INFO.items())
    return f"Here's what I can tell you about the clinic:\n\n{all_info}"
