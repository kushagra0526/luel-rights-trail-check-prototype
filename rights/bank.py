"""Synthetic contributor network, consents and clips for one buyer order, with at most one planted rights gap per clip."""
import datetime as dt
import random

FULL = {"research", "commercial_training", "voice_synthesis", "redistribution"}
DEV = dict(n_clips=400, locations=["TX", "NY", "CA", "IL", "GA", "FL", "OH", "IN"], loc_w=[3, 3, 2, 1, 2, 1, 2, 2],
           residences=None, health_p=0.15, conv_p=0.7, face_p=0.15, uses=["research", "commercial_training"],
           delivery="2026-09-30", start="2026-03-01")
MISTAKES = ["MISSING_PARTY", "ALL_PARTY", "SCOPE", "REVOKED", "BIPA", "HEALTH", "MINOR", "CONSENT_AFTER_RECORDING", "TITLE_CONFLICT"]
EXPECT = {"MISSING_PARTY": {"MISSING_PARTY", "ALL_PARTY"}, "ALL_PARTY": {"ALL_PARTY"}, "SCOPE": {"SCOPE"}, "REVOKED": {"REVOKED"},
          "BIPA": {"BIPA"}, "HEALTH": {"HEALTH"}, "MINOR": {"MINOR"}, "CONSENT_AFTER_RECORDING": {"CONSENT_AFTER_RECORDING", "ALL_PARTY"},
          "TITLE_CONFLICT": {"TITLE_CONFLICT"}}
ONE_PARTY = None


def iso(d):
    return d.isoformat()


def make(seed, cfg=None):
    c = {**DEV, **(cfg or {})}
    r = random.Random(seed)
    start = dt.date.fromisoformat(c["start"])
    persons, consents, clips, labels = {}, [], [], {}
    pid = cid = 0

    def person(loc, adult=True, age=None):
        nonlocal pid
        pid += 1
        a = age if age is not None else r.randrange(19, 70)
        rec_ref = start + dt.timedelta(days=90)
        dob = rec_ref - dt.timedelta(days=int(a * 365.25) + r.randrange(0, 300))
        p = f"P{pid:05d}"
        persons[p] = dict(id=p, dob=iso(dob), residence=loc)
        return p

    def consent(p, signed, by, **kw):
        nonlocal cid
        cid += 1
        x = dict(id=f"C{cid:05d}", person=p, signed_at=iso(signed), revoked_at=None, scopes=set(FULL), health=True,
                 biometric_release=True, guardian=False, collected_by=by)
        x.update(kw)
        consents.append(x)
        return x

    uses = set(c["uses"])
    for i in range(c["n_clips"]):
        loc = r.choices(c["locations"], c["loc_w"])[0]
        rec = start + dt.timedelta(days=r.randrange(0, 150))
        mistake = r.choice(MISTAKES) if r.random() < 0.55 else None
        if mistake == "ALL_PARTY":
            loc = r.choice(["CA", "FL", "PA", "WA"])
        if mistake == "BIPA":
            loc = "IL"
        contrib = person(loc)
        consent(contrib, rec - dt.timedelta(days=r.randrange(1, 60)), contrib)
        speakers, faces = [contrib], []
        conv = r.random() < c["conv_p"] or mistake in ("ALL_PARTY", "MISSING_PARTY", "MINOR")
        other = None
        health = r.random() < c["health_p"] or mistake == "HEALTH"
        if conv:
            other = person(loc, age=16 if mistake == "MINOR" else None)
            speakers.append(other)
            if mistake == "MINOR":
                persons[other]["dob"] = iso(rec - dt.timedelta(days=int(16.5 * 365.25)))
            elif r.random() < 0.05:                        # look-alike: turned 18 exactly on the recording day
                persons[other]["dob"] = iso(rec.replace(year=rec.year - 18))
            if mistake not in ("ALL_PARTY", "MISSING_PARTY"):
                by = contrib if r.random() < 0.8 else f"P{r.randrange(1, max(2, pid)):05d}"   # look-alike: filed by another account
                kw = {}
                signed = rec - dt.timedelta(days=r.randrange(0, 20))
                if mistake == "CONSENT_AFTER_RECORDING":
                    signed = rec + dt.timedelta(days=r.randrange(1, 30))
                if mistake == "SCOPE":
                    kw["scopes"] = FULL - {r.choice(sorted(uses))}
                if mistake == "REVOKED":
                    kw["revoked_at"] = iso(dt.date.fromisoformat(c["delivery"]) - dt.timedelta(days=r.randrange(1, 60)))
                elif r.random() < 0.04:                    # look-alike: revoked after delivery -> notify, still delivered
                    kw["revoked_at"] = iso(dt.date.fromisoformat(c["delivery"]) + dt.timedelta(days=r.randrange(1, 60)))
                if mistake == "BIPA":
                    kw["biometric_release"] = False
                if mistake == "HEALTH":
                    kw["health"] = False
                consent(other, signed, by, **kw)
        elif mistake in ("SCOPE", "REVOKED", "BIPA", "HEALTH", "CONSENT_AFTER_RECORDING"):
            k = consents[-1]                               # the contributor's own consent carries the gap
            if mistake == "SCOPE":
                k["scopes"] = FULL - {r.choice(sorted(uses))}
            elif mistake == "REVOKED":
                k["revoked_at"] = iso(dt.date.fromisoformat(c["delivery"]) - dt.timedelta(days=r.randrange(1, 60)))
            elif mistake == "BIPA":
                k["biometric_release"] = False
            elif mistake == "HEALTH":
                k["health"] = False
            else:
                k["signed_at"] = iso(rec + dt.timedelta(days=r.randrange(1, 30)))
        if r.random() < c["face_p"] and not conv:
            faces.append(contrib)
        h = f"h{i:05d}"
        clips.append(dict(id=f"CL{i:05d}", contributor=contrib, recorded_at=iso(rec), location=loc, speakers=speakers,
                          faces=faces, health=health, audio_hash=h))
        labels[f"CL{i:05d}"] = mistake
        if mistake == "TITLE_CONFLICT":                    # same audio re-uploaded by someone else
            thief = person(loc)
            consent(thief, rec - dt.timedelta(days=5), thief)
            clips.append(dict(id=f"CL{i:05d}b", contributor=thief, recorded_at=iso(rec), location=loc, speakers=list(speakers),
                              faces=[], health=health, audio_hash=h))
            labels[f"CL{i:05d}b"] = "TITLE_CONFLICT"
    order = dict(uses=uses, delivery_date=c["delivery"])
    return clips, consents, persons, order, labels
