function toggle(q) {
    const togtarget = document.querySelectorAll(q)
    togtarget.forEach(el => {el.classList.toggle("collapse") })
    const anchor = q.match(/#[a-z_\-]+/)
    if (anchor && anchor[0]) {
        history.replaceState("", document.title, window.location.pathname+anchor)
    }
}
function show(q) {
    const els = document.querySelectorAll(q)
    els.forEach(el => {el.classList.remove("collapse")})
}
function hide(q) {
    const els = document.querySelectorAll(q)
    els.forEach(el => {el.classList.add("collapse")})
}
function settitle(q) {
    try {
        const title = document.querySelector(q).querySelector("h3").innerText
        document.og_title = document.title
        document.title = `${title} - ${document.og_title}`
    } catch(e) {console.debug(`not setting title for ${q}; probably no h3 (err: ${e})`)}
}
function unsettitle() {
    if (document.og_title) {
        document.title = document.og_title
    }
}
function opendecklist(q) {
    hide(".decklist")
    show(q)
    settitle(q)
    window.location.replace(window.location.pathname+window.location.search+q)
}
function closedecklist(q) {
    hide(q)
    unsettitle()
    history.replaceState(null, "", window.location.pathname+window.location.search)
}
function togglegfx() {
    toggle(".deck_gfx")
    toggle(".deck_txt")
}
function showteammatches(tslug) {
    hide("#matches .match") // hide all
    show(`#matches .t_${tslug}`) // show matching

    show("#matches > .togglable")
    show("#matchreset")
    show("#keymatch-expl")
    hide("#keymatch-showing")
    window.location.hash = "#matches"
}
function show_wins() {
    hide("#sightings tbody tr")
    show("#sightings .winner")
    show("#sightings > .togglable")
    show("#sightingsreset")
    show("#wins-expl")
    hide("#wins-filter")
    hide(".event-filters")
    window.location.hash = "#sightings"
}
function reset_sightings() {
    show("#sightings tr")
    hide("#sightingsreset")
    hide("#wins-expl")
    show("#wins-filter")
    show(".event-filters")
    update_evt_filtering()
}
// match filtering
function showmatches(pid) {
    // show all matches with a given player
    hide("#matches .match")
    hide(".match-badges")
    show(`#matches .p_${pid}`)
    show(`#matches .p_${pid} .match-badges`)

    show("#matches > .togglable")
    show("#matchreset")
    hide("#keymatch-expl")
    hide("#keymatch-showing")
    hide("#keymatches")
    window.location.hash = "#matches"
    document.querySelector("#matches").scrollIntoView()
}
function show_matchup_matches(arche1, arche2) {
    // show all matches between two archetypes
    // (Note: it's structured as p1/p2 instead of generally a list of
    // archetypes is because some decks can be multi-archetypes and I
    // don't want a search for, for example, Water Allies vs Crux to
    // return for example a Water Crux Allies vs [some rando] match.)
    hide("#matches .match")
    hide(".match-badges")
    show(`[data-p1-archetypes*="${arche1}"][data-p2-archetypes*="${arche2}"]`)
    show(`[data-p1-archetypes*="${arche2}"][data-p2-archetypes*="${arche1}"]`)

    show("#matches > .togglable")
    show("#matchreset")
    hide("#keymatch-expl")
    hide("#keymatch-showing")
    hide("#keymatches")
}
function show_arche_matches(arche1) {
    // show all matches involving an archetype
    hide("#matches .match")
    hide(".match-badges")
    show(`[data-p1-archetypes*="${arche1}"]`)
    show(`[data-p2-archetypes*="${arche1}"]`)

    show("#matches > .togglable")
    show("#matchreset")
    hide("#keymatch-expl")
    hide("#keymatch-showing")
    hide("#keymatches")
}
function show_key_matches() {
    hide("#keymatches")
    hide(".match-badges")
    show("#matchreset")

    // Switch the labels
    hide("#keymatch-expl")
    show("#keymatch-showing")

    hide("#matches .match")
    show("#matches > .togglable")
    show("#matches .keymatch")
}
function show_vid_matches() {
    hide("#showvids")
    hide(".match-badges")
    show("#matchreset")

    hide("#matches .match")
    show("#matches > .togglable")
    show("#matches .hasvideo")
}
function reset_matches() {
    hide("#matchreset")
    hide(".match-badges")
    show("#keymatches")
    show("#matches .match")
    show("#showvids")

    // Switch the labels
    show("#keymatch-expl")
    hide("#keymatch-showing")
}

function opentab(tabbutton, selector) {
    const tabbuttons = tabbutton.parentElement.querySelectorAll(".tab")
    tabbuttons.forEach(el => {el.classList.remove("activetab")})
    tabbutton.classList.add("activetab")

    if (selector === undefined) {
        const tabfor = tabbutton.dataset.tabfor
        selector = `[data-tabof="${tabfor}"]`
    }

    const tabparent = tabbutton.parentElement.parentElement
    const target_tab = tabparent.querySelector(selector)
    // Only sibling tabs and not tabs of other groups in the same area
    const tabs = target_tab.parentElement.querySelectorAll(".tabcontent")
    for (const tab of tabs) {
        if (tab === target_tab) {
            tab.classList.remove("collapse")
        } else {
            tab.classList.add("collapse")
        }
    }
}

function opentabs(tabbutton) {
    const tabfor = tabbutton.dataset.tabfor
    const tabbuttons = document.querySelectorAll(".tab")
    const matchingtabs = document.querySelectorAll(`[data-tabfor="${tabfor}"]`)
    tabbuttons.forEach(el => {el.classList.remove("activetab")})
    matchingtabs.forEach(el => {el.classList.add("activetab")})

    const alltabcontent = document.querySelectorAll(".tabcontent")
    const matchingtabcontent = document.querySelectorAll(`[data-tabof="${tabfor}"]`)
    alltabcontent.forEach(el => {el.classList.add("collapse")})
    matchingtabcontent.forEach(el => {el.classList.remove("collapse")})
}

function get_checked_subtype() {
    const st_radios = document.getElementsByName("subtype")
    let checked_subtype = ""
    if (st_radios.length) {
        for (const el of st_radios) {
            if (el.checked) {
                if (el.value === "(All)") {
                    // Leave checked_subtype as empty
                    break
                }
                checked_subtype = el.value
                break
            }
        }
    }
    return checked_subtype
}

function get_cat_filters() {
    const show_cats = []
    document.querySelectorAll('input[name="category"]').forEach( el => {
        if (el.checked) {
            show_cats.push(el.value)
        }
    })
    return show_cats
}

function get_outcome_filter() {
    const outcome_radios = document.getElementsByName("outcome")
    let checked_outcome = ""
    for (const el of outcome_radios) {
        if (el.checked) {
            if (el.value === "(All)") {
                // Leave as empty
                break
            }
            checked_outcome = el.value
        }
    }
    return checked_outcome

}

function save_filtering(showcats, dl_only, small) {
    /* Save current filters to browser storage for loading on other pages */
    if (typeof dl_only != "undefined" && typeof small != "undefined") {
        const evt_cbs = {
            dl_only: (dl_only ? 1:0),
            small: (small ? 1:0),
        }
        window.localStorage.setItem("evt-cbs", JSON.stringify(evt_cbs))
    }

    if (typeof showcats != "undefined") {
        window.localStorage.setItem("evt-cat-filters", JSON.stringify(showcats))
    }
}

function load_filters() {
    const saved_cbs = window.localStorage.getItem("evt-cbs")
    if (saved_cbs) {
        try {
            const { dl_only, small } = JSON.parse(saved_cbs)
            const cb_dl = document.getElementById("cb_decklists")
            if (cb_dl) {
                cb_dl.checked = dl_only
            }
            const cb_small = document.getElementById("cb_small_events")
            if (cb_small) {
                cb_small.checked = small
            }
        } catch (err) {
            console.error("Error loading check boxes:",err)
        }
    }
    const saved_cats = window.localStorage.getItem("evt-cat-filters")
    if (saved_cats) {
        try {
            const cats = JSON.parse(saved_cats)
            const catboxes = document.getElementsByName("category")
            for (const cat_cb of catboxes) {
                if (cats.includes(cat_cb.value)) {
                    cat_cb.checked = true
                } else {
                    cat_cb.checked = false
                }
            }
        } catch (err) {
            console.error("Error loading saved category filters:", err)
        }
    }
}

function update_evt_filtering() {
    /* Filtering for fully-static event / sightings listing only.
     * Dynamically-loaded sightings use populate_sightings()
     */
    const decklist_cb = document.getElementById("cb_decklists")
    let decklists_only = false
    if (decklist_cb) {
        decklists_only = decklist_cb.checked
    }
    const small_evts_cb = document.getElementById("cb_small_events")
    let small_events = false
    if (small_evts_cb) {
        small_events = small_evts_cb.checked
    }

    const checked_subtype = get_checked_subtype()
    const show_cats = get_cat_filters()
    if (decklist_cb && small_evts_cb) {
        save_filtering(show_cats, decklist_cb.checked, small_evts_cb.checked)
    } else {
        save_filtering(show_cats)
    }

    // Filter events (e.g. on homepage, season page)
    document.querySelectorAll('.season .evt').forEach( el => {
        if (decklists_only && el.dataset["decklists"] == "0") {
            el.classList.add("collapse")
        } else if (!small_events && parseInt(el.dataset["playercount"]) < 20
                    && el.dataset["category"] !== "worlds") {
                    // Special case: show Worlds (2024) even though it's "small"
            el.classList.add("collapse")
        } else {
            if ( show_cats.includes(el.dataset["category"]) ) {
                el.classList.remove("collapse")
            } else {
                el.classList.add("collapse")
            }
        }
    })

    // Filter rows (e.g. on archetype page)
    document.querySelectorAll('.p-row').forEach( el => {
        let el_sts = []
        if (el.dataset.hasOwnProperty("subtypes")) {
            el_sts = JSON.parse(el.dataset["subtypes"])
        }

        if (decklists_only && el.dataset["decklists"] == "0") {
            el.classList.add("collapse")
        } else if (!small_events && parseInt(el.dataset["playercount"]) < 20) {
            el.classList.add("collapse")
        } else {
            if ( show_cats.includes(el.dataset["category"]) &&
                 ( !checked_subtype || el_sts.includes(checked_subtype) ) ) {
                el.classList.remove("collapse")
            } else {
                el.classList.add("collapse")
            }
        }
    })
}

function copypermalink() {
    toclipboard(window.location)
}

function omnidexexport(q) {
    const textarea = document.querySelector(q)
    toclipboard(textarea.textContent)
}

function toclipboard(text) {
    if (window.isSecureContext) {
        navigator.clipboard.writeText(text)
    } else {
        console.warn("Can't to clipboard (not a secure context)")
        console.log(text)
    }
}

function carddetail(c) {
    c.classList.toggle("dblclicked")
    c.querySelector(".carddeets")?.classList.toggle("collapse")
}
function flipcard(event, c) {
    event.stopPropagation()
    c.querySelector(".cardfront").classList.toggle("flipped")
    c.querySelector(".cardback").classList.toggle("flipped")
}

function ready(callback) {
  if (document.readyState != "loading") callback()
  else document.addEventListener("DOMContentLoaded", callback)
}

function search_table(el) {
    const searchbox = el.parentElement.querySelector(".searchbox")
    const search_query = searchbox.value
    const trs = document.querySelectorAll(searchbox.dataset["target"])

    for (const tr of trs) {
        if(tr.textContent.toLowerCase().includes(search_query.toLowerCase())) {
            tr.classList.remove("collapse")
        } else {
            tr.classList.add("collapse")
        }
    }
}

function reset_search(el) {
    const searchbox = el.parentElement.querySelector(".searchbox")
    searchbox.value = ""
    const trs = document.querySelectorAll(el.dataset["target"])
    for (const tr of trs) {
        tr.classList.remove("collapse")
    }
    searchbox.focus()
}

async function populate_avatar(el) {
    const pid = el.dataset["pid"]
    const avatardata = await (await fetch(`https://accounts.gatcg.com/user/avatar?userId=${pid}`)).json()
    el.innerHTML = `
    <img src="https://accounts.gatcg.com${avatardata.image}"
        alt="" class="avatar-image" />
    <img src="https://accounts.gatcg.com${avatardata.frame}"
        alt="" class="avatar-frame" />
    `
}

let CARDDATA
async function load_carddata() {
    try {
        CARDDATA = await (await fetch("/card/carddata.json")).json()
    } catch (err) {
        console.error("Error loading data files. Price/frequency information may not load correctly.", err)
    }
}
const NMF = { // Nullable Minified Fields
    "d": "durability",
    "lv": "level",
    "li": "life",
    "p": "power",
    "cm": "cost_memory",
    "cr": "cost_reserve",
    "fs": "fast",
    "bn": "banned",
    "rs": "rarities",
}
let MINDEX
let SET_GROUPS
async function load_mindex() {
    // Load a minified version of index
    try {
        const minified_data = await (await fetch("/card/mindex.json")).json()
        SET_GROUPS = minified_data["__SET_GROUPS"]
        const full_index = {}
        for (cardname in minified_data) {
            if (cardname == "__SET_GROUPS") {
                continue
            }
            const c = minified_data[cardname]
            full_index[cardname] = {
                name: c.n,
                classes: c.cl,
                types: c.t,
                subtypes: c.st,
                effect: c.ef,
                elements: c.el,
                image: c.i,
                in_sets: c.in,
            }
            for (mf in NMF) {
                if (c.hasOwnProperty(mf)) {
                    const ff = NMF[mf]
                    // set full field value to minified field value
                    full_index[cardname][ff] = c[mf]
                }
            }
            // "fr" is from set family, but we can guess what exact set it's
            // actually from by looking at the set codes in that family.
            // It's almost always the shortest one.
            const matching_sets = SET_GROUPS[c.fr].filter(x => c.in.includes(x))
            if (matching_sets.length) {
                const shortest_setcode = matching_sets.reduce((a, b) => a.length <= b.length ? a : b)
                full_index[cardname].from_set = shortest_setcode
            }
        }
        MINDEX = full_index
    } catch (err) {
        console.error("Error loading data files. Card list may not load correctly.", err)
    }
}

function cmpable_price(cardname) {
    // Requires CARDDATA to be loaded
    let price = CARDDATA[cardname]?.price
    if (!price) return -1
    if (price == "N/A (Proxia's Vault)") return 0
    if (price == "Unavailable") return 99999
    if (price.slice(0,1) == "$") return parseFloat(price.slice(1))
    return price
}

function filter_in_set(filt_in_set, card) {
    if (filt_in_set == "any") {
        return true
    } else if (filt_in_set.slice(0,4) == "set:") {
        if (!card.in_sets.includes(filt_in_set.slice(4))) {
            return false
        }
    } else { // set family filter
        const sg = SET_GROUPS[filt_in_set.slice(4)]
        const set_overlap = sg.filter(x => card.in_sets.includes(x))
        if (!set_overlap.length) {
            return false
        }
    }
    return true
}

function filter_from_set(filt_from_set, card) {
    if (filt_from_set == "any") {
        return true
    } else if (filt_from_set.slice(0,4) == "set:") {
        if (card.from_set != filt_from_set.slice(4)) {
            return false
        }
    } else { // set family filter
        const sg = SET_GROUPS[filt_from_set.slice(4)]
        if (!sg || !sg.includes(card.from_set)) {
            return false
        }
    }
    return true
}

const ADVANCED_ELS = [
    "EXALTED", "ARCANE", "ASTRA", "CRUX", "EXIA",
    "LUXEM", "NEOS", "TERA", "UMBRA"
]
function filter_element(filt_el, card) {
    if (filt_el == "any") {
        return true
    } else if (filt_el == "basic") {
        for (el of card.elements) {
            if (ADVANCED_ELS.includes(el)) {
                return false
            }
        }
        return true
    } else if (filt_el == "advanced") {
        for (el of card.elements) {
            if (ADVANCED_ELS.includes(el)) {
                return true
            }
        }
        return false
    } else {
        if (card.elements.includes(filt_el)) {
            return true
        }
        return false
    }
}

function filter_class(filt_class, card) {
    if (filt_class == "any") {
        return true
    } else {
        if (card.classes.includes(filt_class)) {
            return true
        }
        return false
    }
}

function filter_type(filt_type, card) {
    if (filt_type == "any") {
        return true
    } else {
        if (card.types.includes(filt_type)) {
            return true
        }
        return false
    }
}

function filter_arche(filt_arche, card) {
    if (filt_arche == "any") {
        return true
    } else {
        const cardstat = CARDDATA[card.name]
        if (!cardstat) {
            // console.warn(`No cardstat data for ${card.name}`)
            return false
        }
        if (cardstat.top_arche == filt_arche) {
            return true
        }
        return false
    }
}

function filter_min_appearances(filt_minapps, card) {
    const mina = parseInt(filt_minapps)
    const cardstat = CARDDATA[card.name]
    if (!cardstat) {
        // console.warn(`No cardstat data for ${card.name}`)
        return false
    }
    if (cardstat.a >= mina) {
        return true
    }
    return false
}

const RARITIES = {
    1: "C",
    2: "U",
    3: "R",
    4: "SR",
    5: "UR",
    6: "PR",
    7: "CSR",
    8: "CUR",
    9: "CPR"
}
function filter_rarity(filt_rarity, filt_operator, card) {
    if (filt_rarity == "any") {
        return true
    } else {
        const rv = parseInt(filt_rarity)
        if (filt_operator == "eq") {
            if (card.rarities.includes(rv)) {
                return true
            }
            return false
        } else if (filt_operator == "le") {
            if (card.rarities.filter(x => x <= filt_rarity).length) {
                return true
            }
            return false
        } else if (filt_operator == "ge") {
            if (card.rarities.filter(x => x >= filt_rarity).length) {
                return true
            }
            return false
        } else if (filt_operator == "ne") {
            if (card.rarities.includes(rv)) {
                return false
            }
            return true
        } else if (filt_operator == "nl") {
            if (card.rarities.filter(x => x < filt_rarity).length) {
                return false
            }
            return true
        } else if (filt_operator == "ng") {
            if (card.rarities.filter(x => x > filt_rarity).length) {
                return false
            }
            return true
        }
    }
}

function filter_effect(filt_ef, card) {
    filt_ef = filt_ef.trim().toLowerCase()
    if (!filt_ef) {
        return true
    }
    if (card.effect.toLowerCase().includes(filt_ef)) {
        return true
    }
    return false
}

const CARD_FILTERS = {
    "#filt-inset": filter_in_set,
    "#filt-fromset": filter_from_set,
    "#filt-el": filter_element,
    "#filt-class": filter_class,
    "#filt-type": filter_type,
    "#filt-effect": filter_effect,
    "#filt-arche": filter_arche,
    "#filt-minapps": filter_min_appearances,
}

async function update_card_explore_filters() {
    if (!MINDEX) { await load_mindex() }
    if (!CARDDATA) { await load_carddata() }

    // Filter cards according to the selected filter(s) -----------------
    let result_cards = Object.values(MINDEX)
    
    for ( filt_q in CARD_FILTERS ) {
        result_cards = result_cards.filter( (card) => CARD_FILTERS[filt_q](
            document.querySelector(filt_q).value,
            card
        ))
    }
    result_cards = result_cards.filter( (card) => filter_rarity(
        document.querySelector("#filt-rarity").value,
        document.querySelector("#filtop-rarity").value,
        card
    ))

    // Sort cards by the chosen stat ------------------------------------
    const sort_radios = document.getElementsByName("card-sort")
    let sort_stat = ""
    for (const el of sort_radios) {
        if (el.checked) {
            sort_stat = el.value
            break
        }
    }

    for (card of result_cards) {
        if (!CARDDATA[card.name]) {
            // console.warn(`Missing carddata for "${card.name}"`)
            card.quantity="N/A"
            card.sortquantity=""
            continue
        }
        if (sort_stat == "price") {
            card.quantity = CARDDATA[card.name]?.price || "?"
            card.sortquantity = cmpable_price(card.name)
        } else if (sort_stat == "wr-alltime") {
            card.quantity = CARDDATA[card.name]?.wr + "%" || "N/A"
            card.sortquantity = CARDDATA[card.name]?.wr || 0
        } else if (sort_stat == "wr-60d") {
            if (card.quantity = CARDDATA[card.name]?.wr60 == -1) {
                card.quantity = "N/A"
                card.sortquantity = -1
            } else {
                card.quantity = CARDDATA[card.name]?.wr60 + "%" || "N/A"
                card.sortquantity = CARDDATA[card.name]?.wr60 || -2
            }
        } else if (sort_stat == "appr-alltime") {
            card.quantity = CARDDATA[card.name]?.a || 0
            card.sortquantity = CARDDATA[card.name]?.a || 0
        } else if (sort_stat == "appr-60d") {
            card.quantity = CARDDATA[card.name]?.a60 || 0
            card.sortquantity = CARDDATA[card.name]?.a60 || 0
        } else if (sort_stat == "hipster") {
            if (!card.quantity == CARDDATA[card.name]) {
                card.quantity = "N/A"
                card.sortquantity = -1
            } else {
                card.quantity = CARDDATA[card.name].hipster
                card.sortquantity = CARDDATA[card.name].hipster
            }
        }
    }

    result_cards.sort((a,b) => {
        if (a.sortquantity > b.sortquantity) return 1
        if (a.sortquantity == b.sortquantity) return 0
        return -1
    })
    // TODO: allow choosing ascending/descending
    result_cards.reverse()
    
    // Display the results
    display_explore_results(result_cards)
}

function reset_explore_filters() {
    for (filt of ["#filt-inset", "#filt-fromset", "#filt-el", 
        "#filt-rarity", "#filt-class", "#filt-type", "#filt-arche"]) {
        document.querySelector(filt).value = "any"
    }
    document.querySelector("#filt-effect").value = ""
    document.querySelector("#filt-minapps").value = 0
    update_card_explore_filters()
}

function display_explore_results(cardlist) {
    const results_area = document.querySelector("#card-result-list")
    results_area.innerHTML = ""
    let i = 0
    for (card of cardlist) {
        i += 1
        results_area.appendChild(result_card(card, i))
    }
}


function result_card(card, rank) {
    const el = document.createElement("div")
    el.classList.add("cardimg")
    if (card.banned) {
        el.classList.add("banned")
    }
    if (card.removed) {
        el.classList.add("removed")
    }
    el.onclick = () => carddetail(el)
    // TODO: provide back info in Mindex for card-flipping purposes?
    // let back_img = ""
    // if (card.orientations) {
    //     const back = card.orientations[0]
    //     back_img = `<img src="${back.image}" alt="${back.name}" class="cardback flipped"  /><span class="flipper" onclick="flipcard(event, this.parentElement)">↩️</span>`
    // }
    const quant = `<span class="quant">${card.quantity}</span>`

    const cardstat = CARDDATA[card.name]
    let deets2 = ""
    if (cardstat) {
        deets2 = `<ul class="card-deets-list">
            <li><b>Appearances (all time):</b> ${cardstat.a}</li>
            <li><b>Appearances (~60 days):</b> ${cardstat.a60}</li>
            <li><b>Win rate (all time):</b> ${cardstat.wr}</li>
            <li><b>Win rate (~60d, weighted):</b> ${cardstat.wr60 == -1 ? "N/A" : cardstat.wr60}</li>
            <li><b>Hipster rating:</b> ${cardstat.hipster}</li>
            <li><b>TCGP low:</b> ${cardstat.price}</li>
            <li><b>Top archetype:</b> ${cardstat.top_arche ? cardstat.top_arche : "(No data)"}</li>
        </ul>`
    }
    const deets1 = `<div class="carddeets collapse">
        ${rank}. 
        <a href="/card/${slugify(card.name)}.html">${card.name}</a>
        ${ deets2 }
    </div>`
    el.innerHTML = `
        <img class="cardfront" src="${card.image}" loading="lazy" alt="${card.name}" />
        ${quant}
        ${deets1}
    `
    return el
}

function str_thirds(num) {
    // Assuming a float that's in increments of ⅓ (possibly imprecise)
    // return a string in fraction form
    if (parseInt(num) == num) {
        return num.toString()
    }
    let intstr = ''
    if (parseInt(num) != 0) {
        intstr = parseInt(num).toString()
    }
    if (num % 1 < 0.5) {
        return intstr+'⅓'
    }
    return intstr+'⅔'
}

async function calc_trailblazer() {
    if (!CARDDATA) { await load_carddata() }

    const textbox = document.querySelector("#trailblazer-dl")
    const deetbox = document.querySelector("#trailblazer-detail")
    deetbox.innerHTML = ""
    const COMMENT_REGEX = /# (?<comment>.*)$|^(?<comment>[0-9]+ cards)$|^(?<comment>Material deck)$|^(?<comment>Main deck)$|^(?<comment>Sideboard)$/
    const CARD_REGEX = /(?<quantity>[0-9]+) (?<card>.*)$/
    let dl_txt = textbox.value
    let tb_total = 0
    let is_sideboard = false
    let no_points = []
    for (line of dl_txt.split("\n")) {
        const cm = line.match(COMMENT_REGEX)
        if (cm && cm.groups.comment) {
            const comment = cm.groups.comment.trim().toLowerCase()
            if (comment == "sideboard" || comment == "side") {
                is_sideboard = true
            } else if (comment in ['main','main deck','maindeck','material','material deck']) {
                is_sideboard = false
            } else {
                // random comment, no-op
            }
        } else if (line.trim()) {
            const m = line.match(CARD_REGEX)
            if (m && m.groups.card) {
                const cardname = m.groups.card.trim()
                if (cardname in CARDDATA) {
                    const appearances = CARDDATA[cardname].a
                    // material deck cards score triple points
                    const mat_mult = CARDDATA[cardname].mat ? 3 : 1
                    const quant = parseInt(m.groups.quantity)
                    const sb_mult = is_sideboard ? (1.0/3) : 1
                    if (appearances <= 10) {
                        const pts = quant * mat_mult * 2 * sb_mult
                        tb_total += pts
                        if (is_sideboard) { deetbox.innerText += '(Sideboard) ' }
                        deetbox.innerText += `${quant} ${cardname}: ${str_thirds(pts)} points (${appearances} appearances)\n`
                    } else if (appearances <= 100) {
                        const pts = quant * mat_mult * sb_mult
                        tb_total += pts
                        if (is_sideboard) { deetbox.innerText += '(Sideboard) ' }
                        deetbox.innerText += `${quant} ${cardname}: ${str_thirds(pts)} points (${appearances} appearances)\n`
                    } else {
                        no_points.push(cardname)
                    }
                } else {
                    console.error("Couldn't find card data for:", m.groups.card)
                }
            } else {
                console.error("Unknown line in decklist:", line)
            }
        } // else blank line
    }

    const resultfield = document.querySelector("#trailblazer-result")
    resultfield.innerText = str_thirds(tb_total)
    deetbox.innerText += '\nNot worth trailblazer points: ' + no_points.join('; ')
}

async function calc_deck_price(dl) {
    if (!CARDDATA) { await load_carddata() }
    const lines = dl.split('\n')
    let total_price = 0
    const no_price_data = []
    for (const line of lines) {
        const m = line.trim().match(/^([0-9]+) (.*)$/)
        if (m) {
            const quant = parseInt(m[1])
            const cardname = m[2]
            const price = CARDDATA[cardname]?.price
            if (price && price.slice(0,1) == "$") {
                total_price += parseFloat( price.slice(1) ) * quant
            } else {
                if (cardname && price != "N/A (Proxia's Vault)") {
                    no_price_data.push(cardname)
                }
            }
        }
    }
    return {
        "price": total_price.toFixed(2),
        "no_data": no_price_data
    }
}

async function fill_price_and_hipster(container) {
    // Dynamically populate these fields to reduce churn on individual pages
    // during daily deploys.
    // FF: handle prize equivalents the same way as the backend does
    if (!CARDDATA) { await load_carddata() }
    if (!container) {container = document }

    const price_els = container.querySelectorAll(".card-price")
    for (const ps of price_els) {
        const cardname = decodeURIComponent(ps.dataset.cardname)
        ps.innerText = CARDDATA[cardname].price
    }

    const hipster_els = container.querySelectorAll(".card-hipster-rating")
    for (const hs of hipster_els) {
        const cardname = decodeURIComponent(hs.dataset.cardname)
        hs.innerText = CARDDATA[cardname].hipster
    }

    const deck_price_els = container.querySelectorAll(".deck-price")
    for (const ds of deck_price_els) {
        const id = ds.dataset.deckid
        const dltxt = container.querySelector(`#${id} .omniexport`)
        const { price, no_data } = await calc_deck_price(dltxt.innerText)
        ds.innerText = '$' + price
        if (no_data.length) {
            ds.innerText += '* (*Price data could not be found for the following cards: '
            ds.innerText += no_data.join(', ') + ')'
        }
    }
}

function pbox(p) {
    // Return a player box element to be inserted into the DOM
    const el = document.createElement("div")
    el.dataset.name = p.username
    el.dataset.eventcount = p.event_count
    el.classList = ["pprofile"]
    el.innerHTML = `
<a href="/player/${p.id}.html">
    <span class="p-name">${p.username} #${p.id}</span>
    <span class="p-avatar">
        <span class="p-region"><span class="flag" title="${p.region.name}">${p.region.flag}</span></span>
    </span>
</a>
<p class="events-recorded">Events recorded:
    <span class="event-count">${p.event_count}</span>
</p>`
    if (p.last_event) {
        el.innerHTML += `<p class="last-seen">Last seen:
    <a href="${p.last_event.path}">${p.last_event.name}</a>
</p>`
    }
    const pavatar = el.querySelector('.p-avatar')
    if (p.top_champ != "_") {
        pavatar.innerHTML = `<img src="/static/icon/icon-${p.top_champ}.png" alt="${p.top_champ || ""}" loading="lazy" />` + pavatar.innerHTML
    }
    if (p.top_element != "_") {
        pavatar.innerHTML = `<img src="/static/icon/icon-${p.top_element}.png" alt="${p.top_element || ""}" loading="lazy" />` + pavatar.innerHTML
    }
    return el
}

function slugify(s) {
    const unacceptable_chars = /[^A-Za-z0-9 -]+/g
    const whitespace_regex = /\s+/g
    s = s.replaceAll(unacceptable_chars, "")
    s = s.replaceAll(whitespace_regex, "-")
    if (!s) {
        s = "_"
    }
    return s.toLowerCase()
}

// const EVT_CATEGORY = {
//     "worlds": "Worlds",
//     "nationals": "Nationals",
//     "ascent": "Ascent",
//     "regionals": "Regionals",
//     "store-champs": "Store Champs",
//     "regular": "Regular"
// }

function p_row_arche(deck) {
    const anchor = `#deck_${deck.evt_id}_${deck.p_id}`
    const tr = document.createElement("tr")
    tr.classList.add("p-row")
    const nstyles = deck.els.length + deck.arches.length + deck.lineages.length
    tr.classList.add(`n-styles-${nstyles}`)
    let winicon = ""
    if (deck.winner) {
        tr.classList.add("winner")
        winicon = `<span class="win_icon" title="This player won the event">👑</span> `
    }
    tr.dataset.category = deck.evt_cat
    tr.dataset.subtypes = JSON.stringify(deck.els.concat(deck.lineages).concat(deck.subtypes))
    tr.innerHTML = `
    <td class="p_date">${deck.date}</td>
    <td class="playername"><a href="/player/${deck.p_id}.html">${deck.p_name} #${deck.p_id}</a></td>
    <td class="p_event"><a href="/${deck.szn}/${deck.evt_id}.html">${deck.evt_name}</a></td>
    <td class="p_deck"><a href="${anchor}">${deck.d_name}</a>
        <div class="deck-bgs"></div>
    </td>
    <td class="p_placement">${winicon}${deck.place}</td>
    <td class="p_record">${deck.record}</td>
    `
    const dbg = tr.querySelector(".deck-bgs")
    for (const bg of deck.els) {
        dbg.innerHTML += `<img class="deck-bg" src="/static/bg/${slugify(bg)}.jpg" alt="" />`
    }
    for (const bg of deck.arches) {
        dbg.innerHTML += `<img class="deck-bg" src="/static/bg/${slugify(bg)}.jpg" alt="" />`
    }
    for (const bg of deck.lineages) {
        dbg.innerHTML += `<img class="deck-bg" src="/static/bg/${slugify(bg)}.jpg" alt="" />`
    }
    tr.querySelector(".p_deck a").onclick = () => loaddecklist(deck)
    return tr
}

function cardimg(card, hide_overlay, as_token) {
    const el = document.createElement("div")
    el.classList.add("cardimg")
    if (card.banned) {
        el.classList.add("banned")
    }
    if (card.removed) {
        el.classList.add("removed")
    }
    el.onclick = () => carddetail(el)
    let back_img = ""
    if (card.orientations) {
        const back = card.orientations[0]
        back_img = `<img src="${back.image}" alt="${back.name}" class="cardback flipped"  /><span class="flipper" onclick="flipcard(event, this.parentElement)">↩️</span>`
    }
    let quant = ""
    if (!hide_overlay) {
        quant = `<span class="quant">${card.quantity}</span>`
    }
    let deets = ""
    if (!as_token) {
        deets = `<div class="carddeets collapse"><a href="/card/${slugify(card.name)}.html">Card stats</a></div>`
    }
    el.innerHTML = `
        <img class="cardfront" src="${card.image}" loading="lazy" alt="${card.name}" />
        ${back_img}
        ${quant}
        ${deets}
    `
    return el
}

const EL_COLORS = {"Norm": "#ba9", "Fire": "#b30", "Wind": "#6c3", "Water": "#06b", "Arcane": "#23a", "Astra": "#336", "Crux": "#a9d", "Exia": "#310", "Luxem": "#ec4", "Neos": "#a63", "Tera": "#164", "Umbra": "#214", "Exalted/Norm": "#ca7", "Exalted/Fire": "#ca7", "Exalted/Water": "#ca7", "Exalted/Wind": "#ca7", "Unknown": "#000"}

function el_indicator(el) {
    return `<span class="el-indicator" style="background-color: ${EL_COLORS[el]};">&nbsp;</span>`
}

function deck_elementpie(elements) {
    const div = document.createElement("div")
    div.classList.add("element-meta")
    div.innerHTML = `
    <div class="pie-chart">&nbsp;</div>
    <table class="element-table">
        <thead><tr>
            <th>Element</th>
            <th># of cards</th>
            <th>%</th>
        </tr></thead>
        <tbody>
        </tbody>
    </table>
    `
    let gradient = "conic-gradient("
    let cumu = 0
    for (const [el, quant, pct] of elements) {
        gradient += `${EL_COLORS[el]} ${cumu}%, ${EL_COLORS[el]} ${cumu+pct}%, `
        cumu += pct
    }
    gradient = gradient.slice(0, -2) + ")"
    div.querySelector(".pie-chart").style["background"] = gradient

    for (const [el, quant, pct] of elements) {
        div.querySelector("tbody").innerHTML += `
        <tr>
            <th>${el_indicator(el)} ${el}</th>
            <td>${quant}</td>
            <td>${pct}%</td>
        </tr>
        `
    }
    return div
}

function omniformat(dl) {
    s = "\n# Material Deck\n"
    for (const card_o of dl.cards.material) {
        s += `${card_o.quantity} ${card_o.name}\n`
    }
    s += "\n# Main Deck\n"
    for (const card_o of dl.cards.main) {
        s += `${card_o.quantity} ${card_o.name}\n`
    }
    s += "\n# Sideboard\n"
    for (const card_o of dl.cards.sideboard) {
        s += `${card_o.quantity} ${card_o.name}\n`
    }
    return s
}

// FF: pre-cache some decklists?
async function loaddecklist(deck) {
    if (!CARDDATA) { await load_carddata() }
    // FF: can we load carddata in a non-blocking way & still guarantee it's
    // ready by the time it's needed later?
    const d_id = `deck_${deck.evt_id}_${deck.p_id}${deck.topcut ? '_topcut' : ''}`
    if (document.getElementById(d_id)) {
        // Don't re-add decklist item if it's already loaded
        opendecklist(`#${d_id}`)
        return
    }
    // Else fetch the decklist and add it to the document
    const path = `/tts/event_${deck.evt_id}/${deck.p_id}${deck.topcut ? '_topcut' : ''}.json`
    const dl = await (await fetch(path)).json()
    const dlel = document.createElement("div")
    dlel.classList.add("decklist")
    dlel.id = d_id
    let maindeck_total = 0
    for (const card_o of dl.cards.main) {
        maindeck_total += card_o.quantity
    }
    let sb_count = 0
    let sb_points = 0
    for (const card_o of dl.cards.sideboard) {
        sb_count += card_o.quantity
        sb_points += CARDDATA[card_o.name].mat ? 3 : card_o.quantity
    }

    dlel.innerHTML = `
        <button class="prev-deck-btn" onclick="show_previous_deck_dyn(this)" title="Previous deck">⏮</button>
        <div class="decklist-inner">
            <button class="closeX" onclick="closedecklist('#${d_id}')">❌</button>
            <button class="toggle_gfx_btn" onclick="togglegfx()">📝</button>
            <button class="omniexport_btn" onclick="omnidexexport('#${d_id} .omniexport')"><img alt="Export" title="Omnidex Export (copy to clipboard)" src="/static/export.svg" width="24" height="24" /></button>
            <a class="permalink" href="#${d_id}" onclick="copypermalink()">🔗</a>
            <h3>${deck.p_name} #${deck.p_id}'s ${deck.d_name} (${deck.evt_name})${deck.topcut ? ' (Top cut list)' : ''}</h3>
            <div class="decklist-viewbox">
                <h4>Materials <span class="cardcount">(${dl.cards.material.length} cards)</span></h4>
                <ul class="deck_txt material collapse"></ul>
                <div class="deck_gfx material"></div>
                <h4>Maindeck <span class="cardcount">(${maindeck_total} cards)</span></h4>
                <ul class="deck_txt maindeck collapse"></ul>
                <div class="deck_gfx maindeck"></div>
                <h4>Sideboard <span class="cardcount">(${sb_count} cards, ${sb_points} points)</span></h4>
                <ul class="deck_txt sideboard collapse"></ul>
                <div class="deck_gfx sideboard"></div>
                <div class="refs-area"></div>
                <textarea class="omniexport">${omniformat(dl)}</textarea>
                <div class="deck-card-counts">
                    <div class="counts-by-type">
                        <h4>Card Counts</h4>
                        <p class="explanation">(Main deck cards only. Cards with multiple types count for each type. Floating memory counts if the deck has any champion that can use it.)</p>
                        <ul class="deck-stats">
                            <li><b>Floating Memory:</b> ${dl.stats.fm}</li>
                        </ul>
                        <h4>Other Stats</h4>
                        <ul>
                            <li><b>Hipster rating:</b> ${dl.stats.hip}</li>
                            <li><b>Price on TCGPlayer:</b>
                                <span class="deck-price" data-deckid="${d_id}">(Loading)</span>
                                <span class="explanation">(Prices are approximate.)</span>
                            </li>
                        </ul>
                    </div>
                    <div class="counts-by-element">
                        <h4>Elements</h4>
                        <p class="explanation">(Maindeck cards only.)</p>
                    </div>
                </div>
                <div class="similar-decks">
                    <h4>Similar Decks</h4>
                    <p class="explanation">(Similar decks are calculated on a point system where maindeck cards are worth 1 point, material deck cards are 3 points, and sideboards are discounted by ⅓. Only decks with at least 85% overlap are listed, max 10 each before/during/after this event.)</p>
                </div>
            </div>
        </div>
        <button class="next-deck-btn" onclick="show_next_deck_dyn(this)" title="Next deck">⏭</button>
    `
    dlel.querySelector(".counts-by-element").appendChild(
        deck_elementpie(dl.stats.c_els)
    )
    for (const card_o of dl.cards.material) {
        dlel.querySelector(".deck_gfx.material").appendChild(
            cardimg(card_o, (card_o.quantity==1))
        )
        dlel.querySelector(".deck_txt.material").innerHTML += `
            <li>${card_o.name}</li>
        `
    }
    for (const card_o of dl.cards.main) {
        dlel.querySelector(".deck_gfx.maindeck").appendChild(
            cardimg(card_o)
        )
        dlel.querySelector(".deck_txt.maindeck").innerHTML += `
            <li>${card_o.quantity}× ${card_o.name}</li>
        `
    }
    for (const card_o of dl.cards.sideboard) {
        dlel.querySelector(".deck_gfx.sideboard").appendChild(
            cardimg(card_o)
        )
        dlel.querySelector(".deck_txt.sideboard").innerHTML += `
            <li>${card_o.quantity}× ${card_o.name}</li>
        `
    }
    for (const ct in dl.stats.c_types) {
        dlel.querySelector(".deck-stats").innerHTML += `
        <li><b>${ct}</b>: ${dl.stats.c_types[ct]}</li>`
    }
    if (dl.cards.references) {
        dlel.querySelector(".refs-area").innerHTML = `
        <button onclick="toggle('#${d_id} .references')">Glimpse tokens</button>
        <div class="references togglable collapse"></div>
        `
        for (const card_o of dl.cards.references) {
            dlel.querySelector(".references").appendChild(
                cardimg(card_o, true, true)
            )
        }
    }
    if (dl.sim.before?.length) {
        dlel.querySelector(".similar-decks").innerHTML += `<h5>Before this</h5>`
        const ul = document.createElement("ul")
        for (const sim of dl.sim.before) {
            // FF: have delta handle topcut
            let oid = `deck_${sim.p_id}${sim.topcut ? '_topcut' : ''}`
            ul.innerHTML += `<li><a href="/${sim.szn}/${sim.evt_id}.html#${oid}">${sim.p_name} in ${sim.evt_name} (${sim.pct}%) <a class="delta-button" href="/delta.html?e1=${sim.evt_id}&p1=${sim.p_id}&e2=${deck.evt_id}&p2=${deck.p_id}">δ</a></li>`
        }
        dlel.querySelector(".similar-decks").appendChild(ul)
    }
    if (dl.sim.sameday?.length) {
        dlel.querySelector(".similar-decks").innerHTML += `<h5>Same day</h5>`
        const ul = document.createElement("ul")
        for (const sim of dl.sim.sameday) {
            let oid = `deck_${sim.p_id}${sim.topcut ? '_topcut' : ''}`
            ul.innerHTML += `<li><a href="/${sim.szn}/${sim.evt_id}.html#${oid}">${sim.p_name} in ${sim.evt_name} (${sim.pct}%) <a class="delta-button" href="/delta.html?e1=${deck.evt_id}&p1=${deck.p_id}&e2=${sim.evt_id}&p2=${sim.p_id}">δ</a></li>`
        }
        dlel.querySelector(".similar-decks").appendChild(ul)
    }
    if (dl.sim.after?.length) {
        dlel.querySelector(".similar-decks").innerHTML += `<h5>After this</h5>`
        const ul = document.createElement("ul")
        for (const sim of dl.sim.after) {
            let oid = `deck_${sim.p_id}${sim.topcut ? '_topcut' : ''}`
            ul.innerHTML += `<li><a href="/${sim.szn}/${sim.evt_id}.html#${oid}">${sim.p_name} in ${sim.evt_name} (${sim.pct}%) <a class="delta-button" href="/delta.html?e1=${deck.evt_id}&p1=${deck.p_id}&e2=${sim.evt_id}&p2=${sim.p_id}">δ</a></li>`
        }
        dlel.querySelector(".similar-decks").appendChild(ul)
    }
    if (!dl.sim.before?.length && !dl.sim.sameday?.length && !dl.sim.after?.length) {
        dlel.querySelector(".similar-decks").innerHTML += `<p>(None)</p>`
    }
    attach_decklist_closer(dlel)
    document.querySelector("#dynamic-decklists").appendChild(dlel)
    fill_price_and_hipster(dlel)
    opendecklist(`#${d_id}`)
}

// Pagination tools for smart search of player page
const PAGE_SIZE = 40
let selected_players_list = []
function update_prevnext(i) {
    const j = i+PAGE_SIZE
    const prevbut = document.querySelector("#prev-player-btn")
    const nextbut = document.querySelector("#next-player-btn")
    prevbut.disabled = (i <= 0)
    nextbut.disabled = (j >= playerdata.length)
}
function populate_list(grid_sel, datalist, itemfunc, prev_sel, next_sel) {
    const grid = document.querySelector(grid_sel)
    grid.innerHTML = ""
    let i = parseInt(grid.dataset.start) || 0
    j = i + PAGE_SIZE
    for (const item of datalist.slice(i,j)) {
        grid.appendChild(itemfunc(item))
    }
    const prevbut = document.querySelector(prev_sel)
    const nextbut = document.querySelector(next_sel)
    prevbut.disabled = (i <= 0)
    nextbut.disabled = (j >= datalist.length)
}
function shift_list(delta, grid_sel, datalist, itemfunc, prev_sel, next_sel) {
    const grid = document.querySelector(grid_sel)
    let i = parseInt(grid.dataset.start) || 0
    i += delta
    if (i < 0) { i = 0 }
    grid.dataset.start = i
    populate_list(grid_sel, datalist, itemfunc, prev_sel, next_sel)
}
function next_player_page() {
    shift_list(PAGE_SIZE,
            ".player-grid",
            selected_players_list,
            pbox,
            "#prev-player-btn",
            "#next-player-btn"
    )
}
function prev_player_page() {
    shift_list(-PAGE_SIZE,
            ".player-grid",
            selected_players_list,
            pbox,
            "#prev-player-btn",
            "#next-player-btn"
    )
}
function player_search() {
    const q = document.querySelector("#player-search").value.toLowerCase()
    if (q) {
        selected_players_list = playerdata.filter( (p) => {
            const fulluid = `${p.username} #${p.id}`.toLowerCase()
            if (fulluid.includes(q)) { return true }
            return false
        })
        document.querySelector(".player-grid").dataset.start = 0
        populate_list(".player-grid",
            selected_players_list,
            pbox,
            "#prev-player-btn",
            "#next-player-btn"
        )
    } else {
        reset_player_search()
    }
}
function reset_player_search() {
    document.querySelector("#player-search").value = ""
    selected_players_list = playerdata
    document.querySelector(".player-grid").dataset.start = 0
    populate_list(".player-grid",
        selected_players_list,
        pbox,
        "#prev-player-btn",
        "#next-player-btn"
    )
}

let filtered_sightings = []
function populate_sightings() {
    const checked_subtype = get_checked_subtype()
    const show_cats = get_cat_filters()
    const selected_outcome = get_outcome_filter()
    filtered_sightings = all_sightings.filter( (item) => {
        let item_combo_types = item.els.concat(item.arches).concat(item.subtypes).concat(item.lineages)
        if (checked_subtype && !item_combo_types.includes(checked_subtype)) {
            return false
        }
        if (!show_cats.includes(item.evt_cat)) {
            return false
        }
        if (selected_outcome === "wins" && !item.winner) {
            return false
        }
        if (selected_outcome === "high" && !item.high) {
            return false
        }
        return true
    })
    populate_list("#sightings-body",
        filtered_sightings,
        p_row_arche,
        "#prev-sightings-btn",
        "#next-sightings-btn"
    )
}
function update_sighting_filtering() {
    document.querySelector("#sightings-body").dataset.start = 0
    populate_sightings()
}
function next_sightings_page() {
    shift_list(PAGE_SIZE,
        "#sightings-body",
        filtered_sightings,
        p_row_arche,
        "#prev-sightings-btn",
        "#next-sightings-btn"
    )
}
function prev_sightings_page() {
    shift_list(-PAGE_SIZE,
        "#sightings-body",
        filtered_sightings,
        p_row_arche,
        "#prev-sightings-btn",
        "#next-sightings-btn"
    )
}

function make_tables_sortable() {
    // Adapted from - https://stackoverflow.com/a/49041392
    // Posted by Nick Grealy, modified by community.
    // Retrieved 2026-03-02, License - CC BY-SA 4.0
    const sortable_ths = document.querySelectorAll('.sortable th')
    const getCellValue = (tr, idx) => {
        const text = tr.children[idx].innerText || tr.children[idx].textContent
        if (text && text.slice(0,1) == "$") {
            return text.slice(1)
        }
        if (text && text.slice(-1) == "%") {
            return text.slice(0,-1)
        }
        if (text && text.trim() == "N/A (Proxia's Vault)") return "0"
        return text
    }
    const comparer = (idx, asc) => (a, b) => ((v1, v2) =>
        v1 !== '' && v2 !== '' && !isNaN(v1) && !isNaN(v2) ? v1 - v2 : v1.toString().localeCompare(v2)
        )(getCellValue(asc ? a : b, idx), getCellValue(asc ? b : a, idx));

    for (const th of sortable_ths) {
        th.addEventListener('click', (() => {
            const table = th.closest('table')
            Array.from(table.querySelectorAll('tbody tr'))
                .sort(comparer(Array.from(th.parentNode.children).indexOf(th), this.asc = !this.asc))
                .forEach(tr => table.tBodies[0].appendChild(tr) );
        }))
    }
}

function show_previous_deck(btn) {
    const thisdeck = btn.closest(".decklist")
    const newdeck = thisdeck.previousElementSibling
    if (!newdeck || !newdeck.classList.contains("decklist")) {
        return false
    }
    unsettitle()
    opendecklist(`#${newdeck.id}`)
}
function show_next_deck(btn) {
    const thisdeck = btn.closest(".decklist")
    const newdeck = thisdeck.nextElementSibling
    if (!newdeck || !newdeck.classList.contains("decklist")) {
        return false
    }
    unsettitle()
    opendecklist(`#${newdeck.id}`)
}
function sighting_match_id(item, id) {
    const [evt_id, p_id, topcut] = id.slice(5).split("_")
    if (item.evt_id == parseInt(evt_id) && item.p_id == parseInt(p_id)) {
        if (!topcut && !item.topcut) {
            return true
        } else if (topcut && item.topcut) {
            return true
        }
    }
    return false
}
function show_previous_deck_dyn(btn) {
    const thisdeck = btn.closest(".decklist")
    const deck_i = filtered_sightings.findIndex( (item) => sighting_match_id(item, thisdeck.id) )
    unsettitle()
    if (deck_i == -1) {
        // Not found in the current list at all. I guess just close the list?
        thisdeck.click()
    } else if (deck_i > 0) {
        loaddecklist(filtered_sightings[deck_i - 1])
    } else {
        // hit the end. Close the list?
        thisdeck.click()
    }
}
function show_next_deck_dyn(btn) {
    const thisdeck = btn.closest(".decklist")
    const deck_i = filtered_sightings.findIndex( (item) => sighting_match_id(item, thisdeck.id) )
    unsettitle()
    if (deck_i == -1) {
        // Not found in the current list at all. I guess just close the list?
        thisdeck.click()
    } else if (deck_i + 1 < filtered_sightings.length) {
        loaddecklist(filtered_sightings[deck_i + 1])
    } else {
        // hit the end. close the list, ig?
        thisdeck.click()
    }
}

function close_all(event) {
    if (event.key === "Escape") {
        closedecklist(".decklist")
    }
}

function h_scrollable(el) {
    el.addEventListener("pointerdown", (evt) => {
        evt.preventDefault()
        el.setPointerCapture(evt.pointerId)
    })
    el.addEventListener("pointerup", (evt) => {
        evt.preventDefault()
        el.setPointerCapture(evt.pointerId)
    })
    el.addEventListener("pointermove", (evt) => {
        if (el.hasPointerCapture(evt.pointerId) && evt.isPrimary) {
            el.scrollLeft -= evt.movementX
            evt.preventDefault()
        }
    })
}

function attach_decklist_closer(el) {
    el.addEventListener("click", (evt) => {
        if (evt.target.href) {
            // is a link, do the default after closing this
            el.classList.add("collapse")
        }
        else if (!evt.target.classList.contains("decklist")) {
            evt.preventDefault()
        } else {
            el.classList.add("collapse")
            history.replaceState(null, "", window.location.pathname+window.location.search)
            if (document.og_title) {
                document.title = document.og_title
            }
        }
    })
}

ready(() => {
    // Open hash on page-load
    if (window.location.hash) {
        //console.debug("hash:",window.location.hash)
        const defaultobj = document.querySelector(window.location.hash)
        if (defaultobj && defaultobj.classList.contains("collapse")) {
            defaultobj.classList.remove("collapse")
            settitle(window.location.hash)
        } else if (window.location.hash.startsWith("#deck_") && document.querySelector("#dynamic-decklists")) {
            const deck = all_sightings.find( (item) => sighting_match_id(item, window.location.hash.slice(1)) )
            loaddecklist(deck)
        } else {
            q = `${window.location.hash} > .togglable.collapse`
            //collapsedChildren = document.querySelectorAll(q)
            show(q)
        }
    }

    // Re-apply event filters
    if (document.querySelector(".event-filtering")) {
        load_filters()
        update_evt_filtering()
    }

    // Attach decklist closing events
    document.querySelectorAll(".decklist").forEach(attach_decklist_closer)

    // Set up find-as-you-type delay (if needed)
    let typingTimer
    const typeInterval = 200
    const searchbox = document.querySelector(".searchbox")
    if (searchbox) {
        searchbox.addEventListener('keyup', (event) => {
            clearTimeout(typingTimer)
            typingTimer = setTimeout(() => {search_table(event.target)}, typeInterval)
        })
    }

    const playersearch = document.querySelector("#player-search")
    if (playersearch) {
        playersearch.addEventListener('keyup', (event) => {
            clearTimeout(typingTimer)
            typingTimer = setTimeout(() => {player_search()}, typeInterval)
        })
        selected_players_list = playerdata
    }

    const explorercontrols = document.querySelector("#explorer-controls")
    if (explorercontrols) {
        explorercontrols.querySelectorAll("input").forEach(
            el => el.addEventListener("change", update_card_explore_filters)
        )
        explorercontrols.querySelectorAll("select").forEach(
            el => el.addEventListener("change", update_card_explore_filters)
        )
        update_card_explore_filters()
    }

    fill_price_and_hipster()

    document.querySelectorAll(".player-omni-avatar").forEach(populate_avatar)
    make_tables_sortable()

    document.addEventListener('keydown', close_all)
})

