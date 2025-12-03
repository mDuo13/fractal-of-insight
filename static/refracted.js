let currentEvent
let eventList = []
let achievements = []

const EVT_LIST = "refractedEventList"
const STORAGE_PREFIX = "refractedEvent"
const DEFAULT_PLAYER_OPTION = `<option value="0">(Select)</option>`

function load_saved_events() {
    const saved_evt_data = window.localStorage.getItem(EVT_LIST)
    if (!saved_evt_data) {
        return
    }
    try {
        eventList = JSON.parse(saved_evt_data)
    } catch (err) {
        eventList = []
        console.log(`Error ${err} parsing saved event list. Wiping.`)
        window.localStorage.setItem(EVT_LIST, "[]")
    }

    const evtbox = document.querySelector("#selectevent")
    for (const evt of eventList) {
        const evt_id = parseInt(evt.slice(STORAGE_PREFIX.length))
        const lbl = document.createElement("label")
        lbl.innerHTML = `<input type="radio" name="savedevts" value="${evt}" /> Event #${evt_id}`
        lbl.classList.add("saved-event")
        evtbox.appendChild(lbl)
    }
}

function reset_evt() {
    currentEvent = {}
    achievements = []
    hide("#evt-omni-id-loader")
    const saved_event_radios = document.querySelectorAll(".saved-event input")
    for (const sei of saved_event_radios) { sei.checked = false }
    document.querySelector("#evt-omni-id").value = ""
    document.querySelector("#evt-name").innerText = ""
    document.querySelector("#evt-num-entrants").innerText = ""
    document.querySelector("#a-a-player").innerHTML = DEFAULT_PLAYER_OPTION
    const records = document.querySelectorAll("#achievements-awarded .achievement-record")
    for (const arecord of records) { arecord.remove() }
}

async function load_saved() {
    const selected_evt_radio = document.querySelector(".saved-event input:checked")
    if (!selected_evt_radio) {
        console.warn("No event selected to load.")
        return
    }
    const evt_storage_id = selected_evt_radio.value
    const evt_str = window.localStorage.getItem(evt_storage_id)
    const evt = JSON.parse(evt_str)
    document.querySelector("#evt-omni-id").value = evt.event_id
    await fetchevt()
    achievements = evt.achievements
    for (const a of achievements) {
        show_achievement_record(a)
    }
    
}

async function omnilookup(event_id) {
    const e = await (await fetch(`https://api.gatcg.com/omnidex/events/${event_id}`)).json()
    e.players = await (await fetch(`https://api.gatcg.com/omnidex/events/${event_id}/players`)).json()
    return e
}

async function fetchevt(evt) {
    if (evt) { evt.preventDefault() }
    const event_id = document.querySelector("#evt-omni-id").value
    if (!event_id) {
        console.error("No omni ID to look up")
        return
    }
    show("#evt-omni-id-loader")
    currentEvent = await omnilookup(event_id)
    hide("#evt-omni-id-loader")
    document.querySelector("#evt-name").innerText = currentEvent.name
    document.querySelector("#evt-num-entrants").innerText = currentEvent.players.length
    const d = new Date(currentEvent.startedAt)
    document.querySelector("#evt-date").innerText = d.toLocaleDateString()
    const poptions = document.querySelector("#a-a-player")
    poptions.innerHTML = DEFAULT_PLAYER_OPTION
    for (const p of currentEvent.players) {
        const popt = document.createElement("option")
        popt.value = p.id
        popt.innerText = `${p.username} #${p.id}`
        poptions.appendChild(popt)
    }
}

async function show_add(atag) {
    const aname = atag.dataset["aname"]
    const popup = document.querySelector("#add-achievement-popup")
    const preview = document.querySelector("#achievement-preview")
    popup.querySelector("#a-a-name").innerText = aname
    const emoji = atag.querySelector(".achievement-emoji")
    if (emoji) {
        preview.querySelector(".achievement-emoji").innerText = emoji.innerText
        preview.querySelector(".achievement-emoji").classList.remove("collapse")
        preview.querySelector(".achievement-img").classList.add("collapse")
    } else {
        const img = atag.querySelector(".achievement-img img")
        const preview_img = preview.querySelector(".achievement-img img")
        preview_img.src = img.src
        preview_img.alt = img.alt
        preview_img.classList.remove("collapse")
        preview.querySelector(".achievement-emoji").classList.add("collapse")
    }
    const desc = atag.querySelector(".achievement-desc")
    if (desc) {
        preview.querySelector(".achievement-desc").innerText = desc.innerText
    }
    const notes = atag.querySelector(".achievement-notes")
    if (notes && notes.innerText) {
        const preview = document.querySelector("#achievement-preview-notes")
        preview.innerText = notes.innerText
        preview.classList.remove("collapse")
    } else {
        document.querySelector("#achievement-preview-notes").classList.add("collapse")
    }

    document.querySelector("#a-a-player").value = 0
    // TODO: mark off players who can't get the achievement
    popup.classList.remove("collapse")
}

function write_evt() {
    let id
    if (currentEvent) {
        id = currentEvent.id
    } else {
        console.warn("Saving with no omni data")
        id = parseInt(document.querySelector("#evt-omni-id").value)
    }
    // Save current set of achievements to local storage
    const storage_id = `refractedEvent${id}`
    const evt_json = {
        "event_id": id,
        "achievements": achievements
    }
    if (!eventList) {
        eventList = [storage_id]
    } else if (!eventList.includes(storage_id)) {
        eventList.push(storage_id)
    }
    
    const evt_str = JSON.stringify(evt_json, null, 0)
    window.localStorage.setItem(storage_id, evt_str)
    const evt_list_str = JSON.stringify(eventList, null, 0)
    window.localStorage.setItem(EVT_LIST, evt_list_str)
}

function save_achievement() {
    const aname = document.querySelector("#a-a-name").innerText
    const rndnum = parseInt(document.querySelector("#a-a-roundnum").value)
    let p_id = parseInt(document.querySelector("#a-a-player").value)
    if (p_id === 0 || p_id === "0") {
        console.log("TODO: implement manual pid selection")
        return
    }
    for (const pa of achievements) {
        if (pa.achievement === aname && pa.player === p_id) {
            console.error("Player has already gotten this achievement.")
            // TODO: display to user properly
            return
        }
    }
    const a = {
        "player": p_id,
        "round": rndnum,
        "achievement": aname
    }
    achievements.push(a)
    show_achievement_record(a)
    write_evt()
    hide("#add-achievement-popup")
}

function show_achievement_record(a) {
    const pname = document.querySelector(`#a-a-player [value="${a.player}"]`).innerText
    const arecord = document.createElement("div")
    arecord.innerHTML = `
        <button class="remove-achievement" onclick="del_achievement(this)">❌</button> ${pname} achieved 
            ${a.achievement} in round ${a.round}.
    `
    arecord.dataset["player"] = a.player
    arecord.dataset["round"] = a.round
    arecord.dataset["aname"] = a.achievement
    arecord.classList.add("achievement-record")
    document.querySelector("#achievements-awarded").append(arecord)
}

function cancel_add() {
    hide("#add-achievement-popup")
}

function del_achievement(btn) {
    const arecord = btn.parentElement
    let old_achievements = achievements
    achievements = []
    for (const a of old_achievements) {
        if (a.player === parseInt(arecord.dataset["player"]) &&
            a.round === parseInt(arecord.dataset["round"]) &&
            a.achievement === arecord.dataset["aname"]) {
                // console.log("Found and deleted")
        } else {
            /*console.log(`${a.player} vs ${parseInt(arecord.dataset["player"])} 
            ${a.round} vs ${parseInt(arecord.dataset["round"])}
            ${a.achievement} vs ${arecord.dataset["aname"]}`)*/
            achievements.push(a)
        }
    }
    arecord.remove()
    write_evt()
}

ready( () => {
    document.querySelector("#evt-select-form").addEventListener("submit", fetchevt)
    load_saved_events()
})
