from rights import check, bank

FULL = {"research", "commercial_training", "voice_synthesis", "redistribution"}


def world(loc="TX", other_consent=True, **kw):
    persons = {"A": dict(id="A", dob="1990-05-01", residence=loc), "B": dict(id="B", dob="1992-07-09", residence=loc)}
    cons = [dict(id="C1", person="A", signed_at="2026-04-01", revoked_at=None, scopes=set(FULL), health=True,
                 biometric_release=True, guardian=False, collected_by="A")]
    if other_consent:
        b = dict(id="C2", person="B", signed_at="2026-04-02", revoked_at=None, scopes=set(FULL), health=True,
                 biometric_release=True, guardian=False, collected_by="A")
        b.update(kw)
        cons.append(b)
    clip = dict(id="X", contributor="A", recorded_at="2026-04-10", location=loc, speakers=["A", "B"], faces=[], health=False, audio_hash="h1")
    order = dict(uses={"research", "commercial_training"}, delivery_date="2026-09-30")
    return [clip], cons, persons, order


def decide(*w):
    res, man = check.check(*w)
    return res["X"]["decision"], {r["code"] for r in res["X"]["reasons"]}, man


def test_clean_conversation_delivered():
    assert decide(*world())[0] == "DELIVER"


def test_second_speaker_missing_one_party_vs_all_party_state():
    assert decide(*world("TX", other_consent=False))[:2] == ("NEEDS_CONSENT", {"MISSING_PARTY"})
    assert decide(*world("CA", other_consent=False))[:2] == ("EXCLUDE", {"ALL_PARTY"})


def test_scope_bipa_revocation():
    assert "SCOPE" in decide(*world(scopes={"research"}))[1]
    assert "BIPA" in decide(*world("IL", biometric_release=False))[1]
    assert decide(*world(revoked_at="2026-08-01"))[0] == "EXCLUDE"
    d, codes, man = decide(*world(revoked_at="2026-10-15"))           # after delivery: deliver, notify the buyer
    assert d == "DELIVER" and man["revocations_to_notify"]


def test_minor_and_eighteenth_birthday():
    clips, cons, persons, order = world()
    persons["B"]["dob"] = "2008-04-10"                                   # 18 on the recording day
    assert decide(clips, cons, persons, order)[0] == "DELIVER"
    persons["B"]["dob"] = "2008-04-11"
    assert decide(clips, cons, persons, order)[1] == {"MINOR"}


def test_consent_filed_by_another_account_counts():
    assert decide(*world(collected_by="Z"))[0] == "DELIVER"


def test_dev_bank_labels_match():
    clips, cons, persons, order, labels = bank.make(4)
    res, _ = check.check(clips, cons, persons, order)
    assert all((res[c["id"]]["decision"] != "DELIVER") == (labels[c["id"]] is not None) for c in clips)
