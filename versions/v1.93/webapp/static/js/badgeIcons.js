// ── Icônes de badges — mutualisé entre dashboard.js et profil.js ───────────
import { ICONS } from "./icons.js";

const BADGE_ICON_NAMES = {
  ex_10: "target", ex_50: "target", ex_100: "target",
  streak_7: "flame", streak_30: "star",
  chapter_mastered: "trophy", exam_pass: "graduationCap",
};

export function badgeIconSvg(badgeId) {
  return ICONS[BADGE_ICON_NAMES[badgeId]] || ICONS.medal;
}
