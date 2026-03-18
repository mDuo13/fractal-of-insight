async function omnilookup(event_id) {
    const e = await (await fetch(`https://api.gatcg.com/omnidex/events/${event_id}`)).json()
    e.players = await (await fetch(`https://api.gatcg.com/omnidex/events/${event_id}/players`)).json()
    return e
}
