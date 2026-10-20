"""Planted rights gaps held vs clean clips delivered.  python evaluate.py [dev|heldout] [out.json]"""
import collections, json, sys
from rights import bank, check


def run(which):
    if which == "heldout":
        h = json.load(open("heldout/config.json"))
        worlds = [(s, h["cfg"]) for s in h["seeds"]]
    else:
        worlds = [(s, None) for s in range(1, 11)]
    R = {m: collections.Counter() for m in ("consent_id_listed", "this")}
    per = collections.defaultdict(collections.Counter)
    misses, false, notify = [], [], 0
    for s, cfg in worlds:
        clips, consents, persons, order, labels = bank.make(s, cfg)
        res, man = check.check(clips, consents, persons, order)
        notify += len(man["revocations_to_notify"])
        ids = {c["id"] for c in consents}
        own = {}
        for c in consents:
            own.setdefault(c["collected_by"], []).append(c["id"])
        for cl in clips:
            lab, r = labels[cl["id"]], res[cl["id"]]
            base_held = not own.get(cl["contributor"])        # baseline: the uploader's account lists a consent id
            for m, held in (("consent_id_listed", base_held), ("this", r["decision"] != "DELIVER")):
                x = R[m]
                if lab:
                    x["bad"] += 1; x["bad_delivered"] += not held
                else:
                    x["clean"] += 1; x["clean_held"] += held
            if lab:
                codes = {q["code"] for q in r["reasons"]}
                per[lab]["n"] += 1; per[lab]["held"] += r["decision"] != "DELIVER"
                per[lab]["right_reason"] += bool(codes & bank.EXPECT[lab])
                if r["decision"] == "DELIVER":
                    misses.append(dict(label=lab, clip=cl))
            elif r["decision"] != "DELIVER":
                false.append(dict(clip=cl, reasons=r["reasons"]))
    return dict(set=which, results={m: dict(v) for m, v in R.items()}, per_type={k: dict(v) for k, v in per.items()},
                revocations_to_notify=notify, misses=misses, false_holds=false)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "dev"
    r = run(which)
    print(which)
    for m, x in r["results"].items():
        print(f"  {m:18s} clips with a rights gap delivered {x.get('bad_delivered', 0):4d}/{x['bad']}   clean clips held {x.get('clean_held', 0):4d}/{x['clean']}")
    for k, v in sorted(r["per_type"].items()):
        print(f"    {k:24s} held {v['held']:3d}/{v['n']:3d}  right reason {v['right_reason']}")
    print(f"  post-delivery revocations to notify: {r['revocations_to_notify']}   misses {len(r['misses'])}  false holds {len(r['false_holds'])}")
    if len(sys.argv) > 2:
        json.dump(r, open(sys.argv[2], "w"), indent=1, default=str)
