"""
Trilogify — Tool 1: fetch_patient_clinical_profile

Pulls a synthetic patient's structured data from the SMART Health IT
FHIR R4 public sandbox. Every field returned is cited to its FHIR
resource type and ID — nothing is inferred or generated from notes.

Log principle: every item carries its FHIR resource ID so every
downstream claim in Tools 3 and 4 is fully traceable.
"""

import httpx                  # async HTTP library for calling the FHIR API
from typing import Any        # lets us type hint functions that return mixed data

# The base URL of the SMART Health IT public FHIR sandbox.
# This is a free database of completely fictional (synthetic) patients.
# No real patient data. No signup required.
FHIR_BASE = "https://r4.smarthealthit.org"


async def fetch_patient_clinical_profile(patient_id: str) -> dict[str, Any]:
    """
    Fetch a patient's conditions, medications, demographics, and labs
    from the SMART FHIR sandbox. Returns a structured profile where
    every item includes its source FHIR resource ID.

    Args:
        patient_id: FHIR Patient resource ID
                    e.g. "87a339d0-8cae-11ee-a9c8-7edc0e1aca1f"

    Returns:
        dict with keys: patient_id, demographics, conditions,
                        medications, labs, fhir_base, data_source
    """

    # httpx.AsyncClient is like opening a browser tab that can make
    # multiple requests. timeout=30 means give up after 30 seconds
    # if the server does not respond.
    async with httpx.AsyncClient(timeout=30.0) as client:

        #  DEMOGRAPHICS 
        # Fetch the Patient resource — this holds name, gender, birthdate
        patient_resp = await client.get(
            f"{FHIR_BASE}/Patient/{patient_id}",
            headers={"Accept": "application/fhir+json"}  # tell server we want FHIR JSON
        )
        patient_resp.raise_for_status()   # crash loudly if request failed (e.g. 404)
        patient_data = patient_resp.json()  # parse the JSON response into a Python dict

        # FHIR stores names as a list because a person can have multiple names
        # (legal name, nickname, etc). We take the first one.
        name = patient_data.get("name", [{}])[0]
        given = " ".join(name.get("given", ["Unknown"]))  # first/middle names as a string
        family = name.get("family", "Unknown")            # surname

        birth_date = patient_data.get("birthDate", "")   # format: "YYYY-MM-DD"
        gender = patient_data.get("gender", "unknown")

        # Calculate the patient's age from their birth date
        age = None
        if birth_date:
            from datetime import date
            birth = date.fromisoformat(birth_date)  # convert string to a date object
            today = date.today()
            # Subtract birth year from today's year, then adjust if birthday
            # hasn't happened yet this year
            age = today.year - birth.year - (
                (today.month, today.day) < (birth.month, birth.day)
            )

        # Build a clean demographics dictionary.
        # fhir_resource tells us exactly where this data came from.
        demographics = {
            "name": f"{given} {family}",
            "age": age,
            "gender": gender,
            "birth_date": birth_date,
            "fhir_resource": f"Patient/{patient_id}"  # the citation / source
        }

        #  CONDITIONS (active diagnoses) 
        # Fetch all active Condition resources for this patient.
        # "clinical-status=active" filters out resolved/historical conditions.
        cond_resp = await client.get(
            f"{FHIR_BASE}/Condition",
            params={"patient": patient_id, "clinical-status": "active"},
            headers={"Accept": "application/fhir+json"}
        )
        cond_resp.raise_for_status()
        # FHIR returns a Bundle — a wrapper object containing a list of resources
        cond_bundle = cond_resp.json()

        conditions = []
        # Loop through each entry in the Bundle
        for entry in cond_bundle.get("entry", []):
            resource = entry.get("resource", {})

            # FHIR codes are stored as a list of "codings" (different code systems
            # like ICD-10, SNOMED, etc). We take the first one available.
            code_obj = resource.get("code", {})
            codings = code_obj.get("coding", [{}])
            coding = codings[0] if codings else {}

            conditions.append({
                "display": coding.get("display") or code_obj.get("text", "Unknown condition"),
                "icd_code": coding.get("code", ""),       # e.g. "C34.10" for lung cancer
                "system": coding.get("system", ""),        # e.g. "http://hl7.org/fhir/sid/icd-10"
                "fhir_resource": f"Condition/{resource.get('id', '')}"  # citation
            })

        # MEDICATIONS (active prescriptions) 
        # MedicationRequest is the FHIR resource for prescriptions
        med_resp = await client.get(
            f"{FHIR_BASE}/MedicationRequest",
            params={"patient": patient_id, "status": "active"},
            headers={"Accept": "application/fhir+json"}
        )
        med_resp.raise_for_status()
        med_bundle = med_resp.json()

        medications = []
        for entry in med_bundle.get("entry", []):
            resource = entry.get("resource", {})

            # The medication name is stored inside medicationCodeableConcept
            med_concept = resource.get("medicationCodeableConcept", {})
            codings = med_concept.get("coding", [{}])
            coding = codings[0] if codings else {}

            # dosageInstruction is a list — take the first instruction
            dosage_list = resource.get("dosageInstruction", [{}])
            dosage = dosage_list[0] if dosage_list else {}

            medications.append({
                "name": coding.get("display") or med_concept.get("text", "Unknown medication"),
                "rxnorm_code": coding.get("code", ""),     # standard drug code
                "dosage_text": dosage.get("text", ""),     # e.g. "500mg twice daily"
                "fhir_resource": f"MedicationRequest/{resource.get('id', '')}"  # citation
            })

        #  LAB RESULTS (recent Observations) 
        # Observation is the FHIR resource for lab results, vital signs, etc.
        # We filter by category=laboratory and sort by most recent first.
        # _count=20 means return max 20 results.
        obs_resp = await client.get(
            f"{FHIR_BASE}/Observation",
            params={
                "patient": patient_id,
                "category": "laboratory",
                "_count": "20",
                "_sort": "-date"          # minus sign means descending (newest first)
            },
            headers={"Accept": "application/fhir+json"}
        )
        obs_resp.raise_for_status()
        obs_bundle = obs_resp.json()

        labs = []
        for entry in obs_bundle.get("entry", []):
            resource = entry.get("resource", {})
            code_obj = resource.get("code", {})
            codings = code_obj.get("coding", [{}])
            coding = codings[0] if codings else {}

            # Lab values can be numeric (valueQuantity) or text (valueString)
            value_quantity = resource.get("valueQuantity", {})
            value_string = resource.get("valueString", "")

            # Build a human-readable value string
            value = (
                f"{value_quantity.get('value')} {value_quantity.get('unit', '')}".strip()
                if value_quantity else value_string or "N/A"
            )

            labs.append({
                "test": coding.get("display") or code_obj.get("text", "Unknown test"),
                "loinc_code": coding.get("code", ""),      # standard lab code
                "value": value,                             # e.g. "7.2 %"
                "date": resource.get("effectiveDateTime", ""),
                "fhir_resource": f"Observation/{resource.get('id', '')}"  # citation
            })

        #  RETURN THE COMPLETE PROFILE 
        return {
            "patient_id": patient_id,
            "demographics": demographics,
            "conditions": conditions,
            "medications": medications,
            "labs": labs[:10],      # only return the 10 most recent labs
            "fhir_base": FHIR_BASE,
            "data_source": "Trilogify — SMART Health IT FHIR R4 public sandbox (synthetic data only)"
        }