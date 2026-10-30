"use strict";
/* Souls of Muse — small pure helpers shared by the portal and its tests (UMD). */
const ALLOWED_TABS = ["topics", "events", "media", "members", "votes"];
function resolveLeague(requestedId, requestedTab, leagueIds, savedId) {
  const ids = Array.isArray(leagueIds) && leagueIds.length ? leagueIds : [];
  const idValid = ids.includes(requestedId);
  const id = idValid ? requestedId : (ids.includes(savedId) ? savedId : ids[0]);
  const tabRaw = String(requestedTab || "topics").toLowerCase();
  const tab = ALLOWED_TABS.includes(tabRaw) ? tabRaw : "topics";
  return { id, tab, idValid };
}
function tabIndexForKey(key, index, count) {
  if (!count) return index;
  if (key === "ArrowRight") return (index + 1) % count;
  if (key === "ArrowLeft") return (index - 1 + count) % count;
  if (key === "Home") return 0;
  if (key === "End") return count - 1;
  return index;
}
const PortalUtils = { ALLOWED_TABS, resolveLeague, tabIndexForKey };
if (typeof module !== "undefined" && module.exports) module.exports = PortalUtils;
if (typeof window !== "undefined") window.PortalUtils = PortalUtils;
