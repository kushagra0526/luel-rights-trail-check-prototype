"""Rights-trail check for a dataset delivery: every person in every clip, against the buyer's uses and the delivery date.

consent = dict(id, person, signed_at, revoked_at|None, scopes=set, health=bool, biometric_release=bool, guardian=bool, collected_by)
person  = dict(id, dob, residence)                      residence: US state code ("IL") or country ("IN", "DE")
clip    = dict(id, contributor, recorded_at, location, speakers=[person ids], faces=[person ids], health=bool, audio_hash)
order   = dict(uses=set, delivery_date)
Dates are ISO strings. Not legal advice: rules are data and every reason names its source.
"""
import datetime as dt

ALL_PARTY = {"CA", "FL", "IL", "MD", "MA", "MT", "NH", "PA", "WA"}   # commonly listed all-party-consent states
CITE = {
    "MISSING_PARTY": "no consent on file for a person who is recorded",
    "ALL_PARTY": "recorded in an all-party-consent state without every speaker's prior consent (e.g. Cal. Penal Code 632)",
    "SCOPE": "consent does not cover the buyer's use",
    "REVOKED": "consent withdrawn before delivery",
    "BIPA": "Illinois biometric identifier (voiceprint/face) without a written release naming purpose and term (740 ILCS 14/15(b))",
    "HEALTH": "health conversation without explicit health-data consent (GDPR Art. 9(2)(a) / DPDP Act s.6)",
    "MINOR": "person under 18 at recording without guardian consent (DPDP Act s.9 / platform policy)",
    "CONSENT_AFTER_RECORDING": "consent signed after the recording",
    "TITLE_CONFLICT": "same audio uploaded by two contributors: chain of title unclear",
}
LEVEL = {"MISSING_PARTY": "NEEDS_CONSENT", "SCOPE": "NEEDS_CONSENT", "BIPA": "NEEDS_CONSENT", "HEALTH": "NEEDS_CONSENT",
         "CONSENT_AFTER_RECORDING": "NEEDS_CONSENT", "ALL_PARTY": "EXCLUDE", "REVOKED": "EXCLUDE", "MINOR": "EXCLUDE",
         "TITLE_CONFLICT": "EXCLUDE"}
RANK = {"DELIVER": 0, "NEEDS_CONSENT": 1, "EXCLUDE": 2}


def D(s):
    return dt.date.fromisoformat(s[:10])


def age_on(dob, day):
    b, d = D(dob), D(day)
    return d.year - b.year - ((d.month, d.day) < (b.month, b.day))


def check(clips, consents, persons, order):
    by_person = {}
    for c in consents:
        by_person.setdefault(c["person"], []).append(c)
    hashes = {}
    for cl in clips:
        hashes.setdefault(cl["audio_hash"], set()).add(cl["contributor"])
    deliver = D(order["delivery_date"])
    out, notify = {}, []
    for cl in clips:
        F = []
        rec = D(cl["recorded_at"])
        people = list(dict.fromkeys(cl["speakers"] + cl["faces"]))
        biometric = bool(cl["speakers"] or cl["faces"])
        for p in people:
            cs = by_person.get(p, [])
            live = [c for c in cs if not c["revoked_at"] or D(c["revoked_at"]) > deliver]
            if not cs:
                F.append(("ALL_PARTY" if cl["location"] in ALL_PARTY and len(cl["speakers"]) > 1 and p in cl["speakers"] else "MISSING_PARTY", p))
                continue
            if not live:
                F.append(("REVOKED", p))
                continue
            for c in cs:
                if c["revoked_at"] and D(c["revoked_at"]) > deliver:
                    notify.append(dict(clip=cl["id"], person=p, revoked_at=c["revoked_at"]))
            prior = [c for c in live if D(c["signed_at"]) <= rec]
            if not prior:
                F.append(("ALL_PARTY" if cl["location"] in ALL_PARTY and len(cl["speakers"]) > 1 and p in cl["speakers"]
                          else "CONSENT_AFTER_RECORDING", p))
                continue
            c = max(prior, key=lambda x: x["signed_at"])
            if not order["uses"] <= c["scopes"]:
                F.append(("SCOPE", f"{p}: missing {', '.join(sorted(order['uses'] - c['scopes']))}"))
            if biometric and "IL" in (persons[p]["residence"], cl["location"]) and not c["biometric_release"]:
                F.append(("BIPA", p))
            if cl["health"] and not c["health"]:
                F.append(("HEALTH", p))
            if age_on(persons[p]["dob"], cl["recorded_at"]) < 18 and not c["guardian"]:
                F.append(("MINOR", p))
        if len(hashes[cl["audio_hash"]]) > 1:
            F.append(("TITLE_CONFLICT", ", ".join(sorted(hashes[cl["audio_hash"]]))))
        decision = max((LEVEL[k] for k, _ in F), key=RANK.get, default="DELIVER")
        out[cl["id"]] = dict(decision=decision, reasons=[dict(code=k, who=w, why=CITE[k]) for k, w in F])
    delivered = [i for i, r in out.items() if r["decision"] == "DELIVER"]
    manifest = dict(order_uses=sorted(order["uses"]), clips_delivered=len(delivered), clips_held=len(out) - len(delivered),
                    license_scope_covered=sorted(order["uses"]), revocations_to_notify=notify)
    return out, manifest
