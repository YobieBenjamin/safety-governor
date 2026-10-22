from hardware_ref.system import build_node, default_policy
node = build_node()
old_signed = node.signed_policy
pol = default_policy(node.measurement); pol["rules"] = [r for r in pol["rules"] if r["action"] != "payments.transfer"]
node.gate.load_policy(node.governance.policy(pol)); new_id = node.gate.policy_id
try:
    node.gate.load_policy(old_signed); print("gate reloaded the older signed policy:", node.gate.policy_id != new_id, "-> rollback REPRODUCED")
except Exception as e:
    print("refused:", e)
