class_name Profile
extends RefCounted
## Commander ranks of the running campaign (0 = not hired). Saved with the campaign.

static var ranks: Dictionary = {}


static func new_campaign() -> void:
	ranks = {}
	for id in Rules.COMMANDER_ORDER:
		ranks[id] = 1 if Rules.COMMANDERS[id]["unlock"] == 0 else 0


static func unlocked_commanders() -> Array[String]:
	var res: Array[String] = []
	for id in Rules.COMMANDER_ORDER:
		if int(ranks.get(id, 0)) > 0:
			res.append(id)
	return res


## Medals to hire a commander (rank 0) or to promote him by one rank.
static func upgrade_cost(id: String) -> int:
	var r := int(ranks.get(id, 0))
	return Rules.COMMANDERS[id]["unlock"] if r == 0 else Rules.rank_up_cost(r)
