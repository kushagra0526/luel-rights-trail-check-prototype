"""Five clips from one delivery: what a 'consent id on file' check ships vs what the rights trail actually covers."""
from rights import check

FULL = {"research", "commercial_training", "voice_synthesis", "redistribution"}
P = {"A": ("1990-05-01", "TX"), "B": ("1992-07-09", "TX"), "C": ("1988-01-20", "CA"), "D": ("1995-03-03", "CA"),
     "E": ("1991-11-11", "IL"), "F": ("2009-09-01", "IN"), "G": ("1985-02-14", "IN")}
persons = {k: dict(id=k, dob=v[0], residence=v[1]) for k, v in P.items()}


def C(i, p, **kw):
    x = dict(id=i, person=p, signed_at="2026-04-01", revoked_at=None, scopes=set(FULL), health=True, biometric_release=True,
             guardian=False, collected_by=p)
    x.update(kw)
    return x


consents = [C("C1", "A"), C("C2", "B", scopes={"research"}), C("C3", "C"), C("C5", "E", biometric_release=False),
            C("C6", "G"), C("C7", "F", health=True, guardian=False), C("C8", "A", revoked_at="2026-11-02")]
clips = [dict(id="clip-01 TX conversation", contributor="A", recorded_at="2026-04-10", location="TX", speakers=["A", "B"], faces=[], health=False, audio_hash="h1"),
         dict(id="clip-02 CA conversation", contributor="C", recorded_at="2026-04-12", location="CA", speakers=["C", "D"], faces=[], health=False, audio_hash="h2"),
         dict(id="clip-03 IL monologue", contributor="E", recorded_at="2026-04-15", location="IL", speakers=["E"], faces=[], health=False, audio_hash="h3"),
         dict(id="clip-04 IN clinic visit", contributor="G", recorded_at="2026-05-02", location="IN", speakers=["G", "F"], faces=[], health=True, audio_hash="h4"),
         dict(id="clip-05 TX walkthrough", contributor="A", recorded_at="2026-04-20", location="TX", speakers=["A"], faces=["A"], health=False, audio_hash="h5")]
order = dict(uses={"research", "commercial_training"}, delivery_date="2026-09-30")

print("Order: research + commercial training, delivery 2026-09-30. Every clip has a consent id on file for its uploader.\n")
res, man = check.check(clips, consents, persons, order)
for cid, r in res.items():
    print(f"  {cid:26s} {r['decision']}")
    for x in r["reasons"]:
        print(f"      {x['code']:15s} {x['who']}: {x['why']}")
print(f"\nManifest: {man['clips_delivered']} delivered, {man['clips_held']} held; licence covered for delivered clips: {', '.join(man['license_scope_covered'])}")
for n in man["revocations_to_notify"]:
    print(f"  notify buyer: {n['person']} revoked on {n['revoked_at']} (after delivery) for {n['clip']}")
