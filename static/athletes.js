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

  function pad2(value) {
    return String(value).padStart(2, "0");
  }

  function formatHhmmss(hours, minutes, seconds) {
    return `${pad2(hours)}:${pad2(minutes)}:${pad2(seconds)}`;
  }

  function inPreferredTargetRange(totalSeconds) {
    return totalSeconds >= (3 * 3600 + 40 * 60) && totalSeconds <= (7 * 3600 + 30 * 60);
  }

  function normalizeTargetFinishTime(value) {
    const text = normalizeIdentity(value);
    if (!text) {
      return null;
    }

    if (isValidHhmmss(text)) {
      return text;
    }

    const hhmmOrHhmmss = text.match(/^(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?$/);
    if (hhmmOrHhmmss) {
      const hours = Number(hhmmOrHhmmss[1]);
      const minutes = Number(hhmmOrHhmmss[2]);
      const seconds = Number(hhmmOrHhmmss[3] || "0");
      if (minutes >= 60 || seconds >= 60) {
        return null;
      }
      return formatHhmmss(hours, minutes, seconds);
    }

    const numberOnly = text.match(/^\d+$/);
    if (numberOnly) {
      if (text.length <= 2) {
        const hours = Number(text);
        if (hours > 23) {
          return null;
        }
        return formatHhmmss(hours, 0, 0);
      }
      if (text.length <= 4) {
        const hoursOnly = Number(text);
        const hhmmHours = Number(text.slice(0, -2));
        const hhmmMinutes = Number(text.slice(-2));
        const hhmmCandidateValid = hhmmHours <= 23 && hhmmMinutes < 60;
        const hhmmCandidateSeconds = hhmmCandidateValid ? (hhmmHours * 3600 + hhmmMinutes * 60) : null;
        const hoursCandidateSeconds = hoursOnly <= 23 ? hoursOnly * 3600 : null;

        if (
          hhmmCandidateSeconds !== null &&
          (inPreferredTargetRange(hhmmCandidateSeconds) || hoursCandidateSeconds === null)
        ) {
          return formatHhmmss(hhmmHours, hhmmMinutes, 0);
        }
        if (hoursCandidateSeconds !== null) {
          return formatHhmmss(hoursOnly, 0, 0);
        }
      }
      return null;
    }

    const decimalHours = Number(text);
    if (!Number.isNaN(decimalHours) && Number.isFinite(decimalHours) && decimalHours > 0 && decimalHours <= 23) {
      const totalSeconds = Math.round(decimalHours * 3600);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;
      return formatHhmmss(hours, minutes, seconds);
    }

    return null;
  }

  function addAthlete(payload) {
    const athlete = normalizeAthleteInput(payload);
    if (!athlete.entry_id && !athlete.bib) {
      throw new Error("missing_identity");
    }
    const normalized = normalizeTargetFinishTime(athlete.target_finish_time);
    if (!normalized) {
      throw new Error("invalid_target");
    }
    athlete.target_finish_time = normalized;
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
    const normalized = normalizeTargetFinishTime(targetFinishTime);
    if (!normalized) {
      throw new Error("invalid_target");
    }
    const rows = loadAthletes();
    const row = rows.find((item) => item.id === athleteId);
    if (!row) {
      return null;
    }
    row.target_finish_time = normalized;
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
    normalizeTargetFinishTime,
    addAthlete,
    updateAthleteTarget,
    deleteAthlete,
    clearAthletes,
    getAthleteById,
  };
})();
