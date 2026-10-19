def motion_targets(obj_num, eid, has_mask):
    if has_mask and obj_num > 27:
        flagged = set(range(6, 15))
    elif eid > 90 or has_mask:
        flagged = set(range(6, 11))
    else:
        return list(range(obj_num))
    return [i for i in range(obj_num) if i not in flagged]
