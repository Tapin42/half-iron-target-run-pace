(() => {
  const STORAGE_KEY = "halfIronTrackedAthletes.v1";

  function parseStoredRows(rawValue) {
    if (!rawValue) {
      return [];
    }
    try {
      const parsed = JSON.parse(rawValue);
      return Array.isArray(parsed) ? parsed : [];
    } catch (_err) {
      return [];
    }
  }

  function loadAthletes() {
    return parseStoredRows(window.localStorage.getItem(STORAGE_KEY));
  }

  function saveAthletes(rows) {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(rows));
  }

  function createAthleteId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    return `athlete-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function normalizeIdentity(value) {
    return (value || "").trim();
  }

  function normalizeAthleteInput(payload) {
    return {
      id: payload.id || createAthleteId(),
      race_slug: normalizeIdentity(payload.race_slug),
      entry_id: normalizeIdentity(payload.entry_id),
      profile_id: normalizeIdentity(payload.profile_id),
      bib: normalizeIdentity(payload.bib),
      name: normalizeIdentity(payload.name),
      division: normalizeIdentity(payload.division),
      target_finish_time: normalizeIdentity(payload.target_finish_time),
    };
  }

  function findByIdentity(rows, payload) {
    const raceSlug = normalizeIdentity(payload.race_slug);
    const normalizedEntryId = normalizeIdentity(payload.entry_id);
    const normalizedBib = normalizeIdentity(payload.bib);
    const raceRows = rows.filter((row) => row.race_slug === raceSlug);

    let entryMatch = null;
    if (normalizedEntryId) {
      entryMatch = raceRows.find((row) => normalizeIdentity(row.entry_id) === normalizedEntryId) || null;
    }

    let bibMatch = null;
    if (normalizedBib) {
      bibMatch = raceRows.find((row) => normalizeIdentity(row.bib) === normalizedBib) || null;
    }

    if (normalizedEntryId) {
      if (entryMatch && normalizedBib && bibMatch && bibMatch.id !== entryMatch.id) {
        return { status: "conflict" };
      }
      if (entryMatch) {
        return { status: "match", athlete: entryMatch };
      }
      return { status: "none" };
    }

    if (normalizedBib) {
      if (bibMatch) {
        return { status: "match", athlete: bibMatch };
      }
      return { status: "none" };
    }

    return { status: "none" };
  }

  function isValidHhmmss(value) {
    const text = normalizeIdentity(value);
    const match = text.match(/^(\d{2}):(\d{2}):(\d{2})$/);
    if (!match) {
      return false;
    }
    const minutes = Number(match[2]);
    const seconds = Number(match[3]);
    return minutes < 60 && seconds < 60;
  }

  function addAthlete(payload) {
    const athlete = normalizeAthleteInput(payload);
    if (!athlete.entry_id && !athlete.bib) {
      throw new Error("missing_identity");
    }
    if (!isValidHhmmss(athlete.target_finish_time)) {
      throw new Error("invalid_target");
    }
    const rows = loadAthletes();
    const identityCheck = findByIdentity(rows, athlete);
    if (identityCheck.status === "match") {
      throw new Error("duplicate_identity");
    }
    if (identityCheck.status === "conflict") {
      throw new Error("conflicting_identity");
    }
    rows.push(athlete);
    saveAthletes(rows);
    return athlete;
  }

  function updateAthleteTarget(athleteId, targetFinishTime) {
    if (!isValidHhmmss(targetFinishTime)) {
      throw new Error("invalid_target");
    }
    const rows = loadAthletes();
    const row = rows.find((item) => item.id === athleteId);
    if (!row) {
      return null;
    }
    row.target_finish_time = normalizeIdentity(targetFinishTime);
    saveAthletes(rows);
    return row;
  }

  function deleteAthlete(athleteId) {
    const rows = loadAthletes();
    const index = rows.findIndex((row) => row.id === athleteId);
    if (index < 0) {
      return null;
    }
    const [deleted] = rows.splice(index, 1);
    saveAthletes(rows);
    return deleted;
  }

  function clearAthletes() {
    saveAthletes([]);
  }

  function getAthleteById(athleteId) {
    return loadAthletes().find((row) => row.id === athleteId) || null;
  }

  window.AthleteStoreClient = {
    STORAGE_KEY,
    loadAthletes,
    saveAthletes,
    findByIdentity,
    isValidHhmmss,
    addAthlete,
    updateAthleteTarget,
    deleteAthlete,
    clearAthletes,
    getAthleteById,
  };
})();
