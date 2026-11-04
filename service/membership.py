"""Persisted, account-bound meeting membership; legacy pair columns remain readable."""


def install(connection):
    connection.executescript("""
      CREATE TABLE IF NOT EXISTS session_members(
        session_id TEXT NOT NULL, participant_id TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('maestro','artist')),
        PRIMARY KEY(session_id,participant_id));
      CREATE INDEX IF NOT EXISTS session_members_participant
        ON session_members(participant_id,session_id);
    """)
    connection.execute("INSERT OR IGNORE INTO session_members SELECT id,maestro_id,'maestro' FROM sessions WHERE maestro_id IS NOT NULL")
    connection.execute("INSERT OR IGNORE INTO session_members SELECT id,artist_id,'artist' FROM sessions WHERE artist_id IS NOT NULL")


def roles(connection, session_id):
    return dict(connection.execute(
        "SELECT participant_id,role FROM session_members WHERE session_id=? ORDER BY role DESC,participant_id",
        (session_id,),
    ).fetchall())


def public(connection, session_id, accounts):
    members = [
        {"id": person, "role": role, "name": accounts.get(person, {}).get("name", person)}
        for person, role in roles(connection, session_id).items()
    ]
    artists = [member for member in members if member["role"] == "artist"]
    return {"members": members, "artists": artists, "artist_ids": [member["id"] for member in artists]}
