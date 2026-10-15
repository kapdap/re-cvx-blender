import struct


class ScdError(ValueError):
    pass


OPCODES = {
    0x00: ("End", (("byte", 1),)),
    0x01: ("If", (("byte", 1),)),
    0x02: ("Else", (("byte", 1),)),
    0x03: ("EndIf", (("byte", 1),)),
    0x04: ("Check", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1))),
    0x05: ("Set", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1))),
    0x06: ("CompareByte", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x07: ("CompareWord", (("byte", 1), ("byte", 1), ("byte", 1), ("ushort", 2))),
    0x08: ("SetValueByte", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x09: ("SetValueWord", (("byte", 1), ("ushort", 2))),
    0x0A: ("SetWallAtari", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x0B: ("SetEtcAtari", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x0C: ("SetFloorAtari", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x0D: ("CheckDeath", (("byte", 1), ("ushort", 2))),
    0x0E: ("CheckItem", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1))),
    0x0F: ("ClearUseItem", (("byte", 1),)),
    0x10: ("CheckUseItem", (("byte", 1),)),
    0x11: ("CheckPlayerItem", (("byte", 1),)),
    0x12: ("SetCinematic", (("byte", 1),)),
    0x13: ("SetCamera", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x14: ("EventOn", (("byte", 1), ("ushort", 2))),
    0x15: ("BGMOn", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x16: ("BGMOff", (("byte", 1),)),
    0x17: ("SEOn", (("byte", 1), ("byte", 1), ("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1))),
    0x18: ("SEOff", (("byte", 1),)),
    0x19: ("VoiceOn", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x1A: ("VoiceOff", (("byte", 1),)),
    0x1B: ("CheckADX", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x1C: ("BGSEOn", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1))),
    0x1D: ("BGSEOff", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x1E: ("CheckADXTime", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1))),
    0x1F: ("SetMessage", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x20: ("SetDisplayObject", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x21: ("CheckDeathEvent", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1))),
    0x22: ("SetCheckEnemy", (("byte", 1), ("ushort", 2))),
    0x23: ("SetCheckItem", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1))),
    0x24: ("SetInitModel", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x25: ("SetEtcAtari2", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x26: ("CheckArmsItem", (("byte", 1),)),
    0x27: ("ChangeArmsItem", (("byte", 1),)),
    0x28: ("SubStatus", (("byte", 1),)),
    0x29: ("SetCameraPause", (("byte", 1),)),
    0x2A: ("SetCamera2", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x2B: ("SetMotionPause", (("byte", 1),)),
    0x2C: ("SetEffect", (("byte", 1), ("ushort", 2))),
    0x2D: ("InitMotionPause", (("byte", 1),)),
    0x2E: ("SetPlayerMotionPause", (("byte", 1),)),
    0x2F: ("InitSetKage", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x30: ("InitMotionPauseEx", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x31: ("PlayerItemLost", (("byte", 1),)),
    0x32: ("SetObjectLink", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0x33: ("SetDoorCall", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x34: ("SetPlayerObjectLink", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0x35: ("SetLight", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x36: ("SetFade", (("int", 4), ("byte", 1))),
    0x37: ("RoomCaseNo", (("byte", 1),)),
    0x38: ("CheckFrame", (("byte", 1), ("byte", 1), ("byte", 1), ("ushort", 2))),
    0x39: ("SetCameraInfo", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x3A: ("SetPlayerMuteki", (("byte", 1),)),
    0x3B: ("SetDefaultModel", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x3C: ("SetMask", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x3D: ("SetLip", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x3E: ("StartMask", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x3F: ("StartLip", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x40: ("SetPlayerStartLookG", (("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0x41: ("SetPlayerStopLookG", (("byte", 1),)),
    0x42: ("SetItemAspd", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x43: ("SetEffectDisplay", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x44: ("SetEffectAmb", (("float", 1), ("float", 1), ("float", 1), ("byte", 1), ("byte", 1))),
    0x45: ("DeleteObjectSE", (("byte", 1),)),
    0x46: ("SetNextRoomBGM", (("byte", 1), ("byte", 1), ("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1))),
    0x47: ("SetNextRoomBGSE", (("byte", 1), ("byte", 1), ("byte", 1), ("ushort", 2), ("ushort", 2), ("byte", 1), ("byte", 1))),
    0x48: ("CallFootSE", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x49: ("CallWeaponSE", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x4A: ("SetYakkyou", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x4B: ("SetLightType", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x4C: ("SetFogColor", (("uint", 4), ("byte", 1))),
    0x4D: ("CheckPlayerItemBlock", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x4E: ("SetEffectBlood", (("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x4F: ("SetCyoutenHenkei", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x50: ("SetObjectMotion", (("byte", 1),)),
    0x51: ("SetObjectEnemyLink", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0x52: ("SetObjectItemLink", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0x53: ("SetEnemyItemLink", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0x54: ("SetEnemyEnemyLink", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0x55: ("StartCyoutenHenkei", (("byte", 1),)),
    0x56: ("SetEffectBloodPool", (("byte", 1), ("byte", 1), ("byte", 1), ("ushort", 2))),
    0x57: ("FixEventCameraPlayer", (("byte", 1),)),
    0x58: ("SetEffectBloodPool2", (("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("ushort", 2))),
    0x59: ("SetObjectObjectLink", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0x5A: ("SetCameraYure", (("byte", 1), ("float", 2))),
    0x5B: ("SetInitCamera", (("byte", 1),)),
    0x5C: ("SetMessageDisplayEnd", (("byte", 1),)),
    0x5D: ("CheckPad", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x5E: ("StartMovie", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x5F: ("StopMovie", (("byte", 1),)),
    0x60: ("CheckTFrame", (("byte", 1), ("byte", 1), ("byte", 1), ("ushort", 2))),
    0x61: ("ClearEventTimer", (("byte", 1),)),
    0x62: ("CheckCamera", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x63: ("SetRandom", (("byte", 1),)),
    0x6407: ("PlayerControl07", (("float", 2), ("float", 2), ("float", 2))),
    0x640D: ("PlayerControl0D", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x6434: ("PlayerControl34", ()),
    0x6480: ("PlayerControl80", ()),
    0x6481: ("PlayerControl81", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x6482: ("PlayerControl82", ()),
    0x6483: ("PlayerControl83", (("byte", 1), ("byte", 1))),
    0x6489: ("PlayerControl89", (("byte", 1), ("byte", 1))),
    0x648B: ("PlayerControl8B", ()),
    0x648E: ("PlayerControl8E", ()),
    0x6496: ("PlayerControl96", (("byte", 1), ("byte", 1))),
    0x65: ("LoadWork", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x6601: ("ObjectControl01", ()),
    0x6608: ("ObjectControl08", ()),
    0x660C: ("ObjectControl0C", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x6614: ("ObjectControl14", (("byte", 1), ("byte", 1))),
    0x6780: ("SubControl80", ()),
    0x678F: ("SubControl8F", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x6793: ("SubControl93", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x6794: ("SubControl94", (("byte", 1), ("byte", 1))),
    0x68: ("LoadWork2", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x6902: ("CommonControl02", (("byte", 1),)),
    0x6903: ("CommonControl03", (("byte", 1),)),
    0x6904: ("CommonControl04", (("byte", 1),)),
    0x6905: ("CommonControl05", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x6906: ("CommonControl06", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x6907: ("CommonControl07", (("float", 2), ("float", 2), ("float", 2))),
    0x6908: ("CommonControl08", (("byte", 1), ("byte", 1), ("ushort", 2), ("ushort", 2))),
    0x6909: ("CommonControl09", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x690A: ("CommonControl0A", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x690B: ("CommonControl0B", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x690C: ("CommonControl0C", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x690D: ("CommonControl0D", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x690F: ("CommonControl0F", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x6910: ("CommonControl10", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x6911: ("CommonControl11", (("byte", 1), ("byte", 1))),
    0x6912: ("CommonControl12", (("byte", 1), ("byte", 1))),
    0x6913: ("CommonControl13", (("byte", 1), ("byte", 1))),
    0x6917: ("CommonControl17", (("byte", 1), ("byte", 1))),
    0x6918: ("CommonControl18", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x6919: ("CommonControl19", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x691A: ("CommonControl1A", (("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0x691B: ("CommonControl1B", (("byte", 1), ("byte", 1), ("float", 2), ("float", 2))),
    0x691C: ("CommonControl1C", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x691D: ("CommonControl1D", (("byte", 1),)),
    0x691E: ("CommonControl1E", (("byte", 1),)),
    0x691F: ("CommonControl1F", (("byte", 1),)),
    0x6920: ("CommonControl20", (("byte", 1),)),
    0x6921: ("CommonControl21", (("byte", 1),)),
    0x6922: ("CommonControl22", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x6924: ("CommonControl24", ()),
    0x6926: ("CommonControl26", (("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0x6928: ("CommonControl28", (("byte", 1), ("byte", 1))),
    0x6929: ("CommonControl29", (("byte", 1), ("byte", 1))),
    0x692A: ("CommonControl2A", (("byte", 1), ("byte", 1))),
    0x692C: ("CommonControl2C", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x692E: ("CommonControl2E", (("byte", 1), ("byte", 1))),
    0x692F: ("CommonControl2F", ()),
    0x6930: ("CommonControl30", (("byte", 1), ("byte", 1))),
    0x6931: ("CommonControl31", (("byte", 1), ("byte", 1))),
    0x6932: ("CommonControl32", (("byte", 1), ("byte", 1))),
    0x6933: ("CommonControl33", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x6934: ("CommonControl34", (("byte", 1), ("byte", 1))),
    0x6935: ("CommonControl35", (("byte", 1), ("byte", 1))),
    0x6A: ("SetEventSkip", (("byte", 1),)),
    0x6B: ("DeleteYakkyou", (("byte", 1),)),
    0x6C: ("SetObjectAlpha", (("byte", 1), ("byte", 1), ("byte", 1), ("sbyte", 1), ("sbyte", 1), ("float", 1), ("float", 1))),
    0x6D: ("SetCyodan", (("float", 4), ("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("byte", 1), ("byte", 1))),
    0x6E: ("SetHEffect", (("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("ushort", 2))),
    0x6F: ("SetObjectPlayerLink", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0x70: ("EffectPush", (("byte", 1),)),
    0x71: ("EffectPop", (("byte", 1),)),
    0x72: ("AreaSearchObject", (("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2))),
    0x73: ("SetLightParameterC", (("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("float", 2), ("float", 2), ("float", 2), ("float", 2), ("float", 2), ("float", 2), ("float", 2))),
    0x74: ("StartLightParameter", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x75: ("SetInitMidiSlot", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x76: ("Set3DSoundFlag", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x77: ("SetSoundVolume", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x78: ("SetLightParameter", (("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("float", 2), ("float", 2))),
    0x79: ("EnemySEOn", (("byte", 1), ("byte", 1), ("byte", 1), ("ushort", 2))),
    0x7A: ("EnemySEOff", (("byte", 1),)),
    0x7B: ("SetWallAtari2", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x7C: ("SetFloorAtari2", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x7D: ("SetEnemyPlayerMotionPos", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x7E: ("SetKageSw", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x7F: ("SetSoundPan", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x80: ("SetInitPony", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x81: ("CheckSubMapBusy", (("byte", 1),)),
    0x82: ("SetDebugLoopEx", (("byte", 1), ("ushort", 2))),
    0x83: ("SoundFadeOut", (("byte", 1),)),
    0x84: ("SetCyoutenHenkeiEx", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("float", 2))),
    0x85: ("StartCyoutenHenkeiEx", (("byte", 1), ("float", 2))),
    0x86: ("SetEasySE", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("short", 2))),
    0x87: ("SetSoundFlagReset", (("byte", 1),)),
    0x88: ("SetEffectUV", (("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("float", 2))),
    0x89: ("SetChangePlayer", (("byte", 1),)),
    0x8A: ("CheckPlayerPoison", (("byte", 1),)),
    0x8B: ("AddObjectSE", (("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("ushort", 2))),
    0x8C: ("RandomTest", (("byte", 1), ("ushort", 2), ("ushort", 2))),
    0x8D: ("SetEventCom", (("byte", 1),)),
    0x8E: ("CheckZombieUpDeath", (("byte", 1), ("ushort", 2))),
    0x8F: ("SetFacePause", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x90: ("SetFaceRe", (("byte", 1),)),
    0x91: ("SetEffectMode", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x92: ("BGSEOff2", (("byte", 1),)),
    0x93: ("BGMOff2", (("byte", 1),)),
    0x94: ("BGSEOn2", (("byte", 1), ("ushort", 2))),
    0x95: ("BGMOn2", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x96: ("SetEffectSensya", (("byte", 1),)),
    0x97: ("SetEffectKokuen", (("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0x98: ("SetEffectSand", (("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("byte", 1), ("byte", 1))),
    0x99: ("EnemyHPUp", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x9A: ("FaceRep", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x9B: ("CheckMovie", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0x9C: ("SetItemMotion", (("byte", 1),)),
    0x9D: ("SetObjectAspd", (("byte", 1), ("byte", 1), ("byte", 1))),
    0x9E: ("SetVibrationFlag", (("byte", 1),)),
    0x9F: ("StartVibration", (("byte", 1),)),
    0xA0: ("MapSystemOn", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0xA1: ("SetTrapDamage", (("byte", 1),)),
    0xA2: ("SetEventLighterFire", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xA3: ("SetPlayerItemLink", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0xA4: ("PlayerKaidanMotion", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xA5: ("SetEnemyRender", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xA6: ("BGMOnEx", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xA7: ("BGMOn2Ex", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xA8: ("SetFogParameterC", (("float", 1), ("float", 1), ("float", 1), ("float", 1), ("float", 1), ("float", 1), ("float", 1), ("float", 1), ("byte", 1))),
    0xA9: ("StartFogParameter", (("byte", 1),)),
    0xAA: ("SetEffectUV2", (("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("float", 2))),
    0xAB: ("SetBGColor", (("uint", 4), ("byte", 1))),
    0xAC: ("CheckMovieTime", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1))),
    0xAD: ("SetEffectType", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xAE: ("PlayerPoison2Cr", (("byte", 1),)),
    0xAF: ("PlayerHandChange", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xB0: ("SetHEffect2", (("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("ushort", 2))),
    0xB1: ("CheckObjectDpos", (("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0xB2: ("GetItem", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xB3: ("SetEtcAtariEnemyPos", (("byte", 1), ("byte", 1), ("byte", 1), ("sbyte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0xB4: ("SetEtcAtariEventPos", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xB5: ("LoadWorkEx", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xB6: ("RoomSoundCase", (("byte", 1),)),
    0xB7: ("ItemPlayerToStorageBox", (("byte", 1),)),
    0xB8: ("ItemStorageBoxToInventoryBox", (("byte", 1),)),
    0xB9: ("SetGridPos", (("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0xBA: ("SetGridPosMoveC", (("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0xBB: ("StartGridPosMove", (("byte", 1),)),
    0xBC: ("EventKill", (("byte", 1),)),
    0xBD: ("SetReTryPoint", (("byte", 1),)),
    0xBE: ("CheckPlayerDPos", (("byte", 1), ("byte", 1), ("sbyte", 1), ("byte", 1), ("byte", 1))),
    0xBF: ("PlayerItemLostEx", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xC0: ("SetCyodanEx", (("int", 4), ("int", 4), ("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0xC1: ("SetArmsItem", (("byte", 1),)),
    0xC2: ("GetItemEx", (("byte", 1), ("byte", 1), ("byte", 1), ("ushort", 2))),
    0xC3: ("SetMatsumotoEffectSand", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xC4: ("VoiceWait", (("byte", 1), ("ushort", 2), ("byte", 1), ("byte", 1), ("byte", 1), ("byte", 1))),
    0xC5: ("StartVoice", (("byte", 1),)),
    0xC6: ("SetGameOver", (("byte", 1),)),
    0xC7: ("PlayerItemChangeM", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xC8: ("SetEffectBakuDrm", (("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0xC9: ("SetPlayerItemTama", (("byte", 1), ("ushort", 2))),
    0xCA: ("ClearEventEffect", (("byte", 1),)),
    0xCB: ("SetEventTimer", (("byte", 1),)),
    0xCC: ("SetEnemyLookFlag", (("byte", 1), ("byte", 1), ("byte", 1))),
    0xCD: ("ReturnTitleEvent", (("byte", 1),)),
    0xCE: ("SetCameraMode", (("byte", 1),)),
    0xCF: ("InitGameItemEx", (("byte", 1),)),
    0xD0: ("SetEnemyLifeM", (("byte", 1), ("ushort", 2))),
    0xD1: ("SetEffectSSize", (("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0xD2: ("SetEffectLinkOffset", (("byte", 1), ("byte", 1), ("byte", 1), ("float", 2), ("float", 2), ("float", 2))),
    0xD3: ("CallRanking", (("byte", 1),)),
    0xD4: ("CallSysSE", (("byte", 1), ("ushort", 2))),
    0xD5: ("Empty", ()),
    0xD6: ("Empty", ()),
    0xD7: ("Empty", ()),
    0xD8: ("Empty", ()),
    0xD9: ("Empty", ()),
    0xDA: ("Empty", ()),
    0xDB: ("Empty", ()),
    0xDC: ("Empty", ()),
    0xDD: ("Empty", ()),
    0xDE: ("Empty", ()),
    0xDF: ("Empty", ()),
    0xE0: ("Empty", ()),
    0xE1: ("Empty", ()),
    0xE2: ("Empty", ()),
    0xE3: ("Empty", ()),
    0xE4: ("Empty", ()),
    0xE5: ("Empty", ()),
    0xE6: ("Empty", ()),
    0xE7: ("Empty", ()),
    0xE8: ("Empty", ()),
    0xE9: ("Empty", ()),
    0xEA: ("Empty", ()),
    0xEB: ("Empty", ()),
    0xEC: ("Empty", ()),
    0xED: ("Empty", ()),
    0xEE: ("Empty", ()),
    0xEF: ("Empty", ()),
    0xF0: ("Empty", ()),
    0xF1: ("Empty", ()),
    0xF2: ("Empty", ()),
    0xF3: ("EWhile2", ()),
    0xF4: ("ComNext", ()),
    0xF5: ("Empty", ()),
    0xF6: ("Empty", ()),
    0xF7: ("Empty", ()),
    0xF8: ("Sleep", (("byte", 1), ("ushort", 2))),
    0xF9: ("Sleeping", (("byte", 1), ("byte", 1))),
    0xFA: ("For", (("byte", 1), ("ushort", 2))),
    0xFB: ("Next", (("byte", 1),)),
    0xFC: ("While", (("byte", 1),)),
    0xFD: ("EWhile", ()),
    0xFE: ("EventNext", ()),
    0xFF: ("EventEnd", (("byte", 1),)),
}


def _decode_arg(kind, raw, endian="<"):
    if kind == "byte":
        return raw[0]
    if kind == "sbyte":
        return struct.unpack("b", raw)[0]
    if kind == "short":
        return struct.unpack(endian + "h", raw)[0]
    if kind == "ushort":
        return struct.unpack(endian + "H", raw)[0]
    if kind == "int":
        return struct.unpack(endian + "i", raw)[0]
    if kind == "uint":
        return struct.unpack(endian + "I", raw)[0]
    if kind == "float":
        if len(raw) == 4:
            return struct.unpack(endian + "f", raw)[0]
        if len(raw) == 2:
            return struct.unpack(endian + "H", raw)[0] / 100.0
        return float(raw[0])
    return bytes(raw)


class ScdInstruction:
    def __init__(self):
        self.offset = 0
        self.size = 0
        self.opcode = 0
        self.name = ""
        self.args = []

    def read(self, data, offset, endian="<"):
        if offset < 0 or offset >= len(data):
            raise ScdError("scd offset out of range")
        b0 = data[offset]
        key = b0
        head = 1
        if offset + 1 < len(data):
            two = (b0 << 8) | data[offset + 1]
            if two > 0xFF and two in OPCODES:
                key = two
                head = 2
        if key not in OPCODES:
            raise ScdError(f"unknown scd opcode {b0:02X} at offset {offset}")
        name, spec = OPCODES[key]
        args = []
        pos = offset + head
        for kind, size in spec:
            if pos + size > len(data):
                raise ScdError(f"truncated scd {name} at offset {offset}")
            args.append(_decode_arg(kind, data[pos : pos + size], endian))
            pos += size
        self.offset = offset
        self.size = pos - offset
        self.opcode = key
        self.name = name
        self.args = args
        return self


class ScdDocument:
    def __init__(self):
        self.offset = 0
        self.size = 0
        self.instructions = []

    def read(self, data, offset=0, endian="<"):
        self.offset = offset
        self.instructions = list(iter_scd_instructions(data, offset, endian))
        if self.instructions:
            last = self.instructions[-1]
            self.size = (last.offset + last.size) - offset
        else:
            self.size = 0
        return self

    def decompile(self):
        lines = []
        for ins in self.instructions:
            if ins.args:
                inner = ", ".join(_format_arg(v) for v in ins.args)
                lines.append(f"{ins.name}({inner})")
            else:
                lines.append(f"{ins.name}()")
        return "\n".join(lines)


def _format_arg(value):
    if isinstance(value, float):
        return f"{value:.5f}".rstrip("0").rstrip(".") if "." in f"{value:.5f}" else str(value)
    return str(value)


def iter_scd_instructions(data, offset=0, endian="<"):
    pos = offset
    while pos < len(data):
        ins = ScdInstruction()
        ins.read(data, pos, endian)
        yield ins
        if ins.size <= 0:
            raise ScdError("scd instruction made no progress")
        pos += ins.size


def parse_scd(data, offset=0, endian="<"):
    return ScdDocument().read(data, offset, endian)


def decode_scd(data, offset=0, endian="<"):
    return parse_scd(data, offset, endian)
