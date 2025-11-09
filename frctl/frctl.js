let mysterycard
let hints_given = []
let past_cards = []
let victories = 0
let ALLSLUGS
let ALLDIALOG

function sleep (delayInMs) {
  return new Promise((resolve) => setTimeout(resolve, delayInMs))
}

async function indexlookup(slug) {
    return await (await fetch(`https://api.gatcg.com/cards/${slug}`)).json()
}

async function populateautocomplete(cards) {
    const ac = document.querySelector("#autocomplete")
    ac.innerHTML = ""
    for (const c of cards) {
        const o = document.createElement("option")
        o.innerText = c.name
        // o.value="🔤"+c.slug
        o.value = c.name
        ac.appendChild(o)
    }
}

async function pressguess(event) {
    event.preventDefault()
    const gb = document.querySelector("#guessbox")
    const guesstext = gb.value
    gb.value = ""
    if (guesstext.length == 0) {
        return
    }
    const {card, results } = await submitguess(guesstext)
    if (card && results) {
        console.log("Guessed", card)
        // console.log("Results:", results)
        addguess(card, results)
    }
}

async function submitguess(name) {
    if (name.slice(0,2) === "🔤") {
        // special case for slugs
        return await guesscard(name.slice(2))
    }
    const resp = await (await fetch(`https://api.gatcg.com/cards/autocomplete?name=${name}`)).json()
    if (resp.length === 0) {
        console.warn(`No card matching "${name}"`)
        return {"card":null, "results":false}
    } else if (resp.length > 1) {
        // check for an exact match
        for (const result of resp) {
            if (result.name.toLowerCase() == name.toLowerCase()) {
                return await guesscard(result.slug)
            }
        }
        // no exact match
        console.debug(`Multiple cards matching "${name}"`)
        populateautocomplete(resp)
        return {"card":null, "results":false}
    }
    return await guesscard(resp[0].slug)
}

async function guesscard(slug) {
    const guess = await indexlookup(slug)
    
    if (guess.name == mysterycard.name) {
        return {"card":guess, "results":true}
    }
    const results = {
        "elements": "❌",
        "cost": "❌",
        "types": "❌",
        "subtypes": "❌",
        "stats": "❌"
    }

    // Elements ---------------
    guess.elements.sort()
    mysterycard.elements.sort()
    if (JSON.stringify(guess.elements) == JSON.stringify(mysterycard.elements)) {
        results.elements = "✅"
    } else {
        for (const el of guess.elements) {
            if (mysterycard.elements.includes(el)) {
                results.elements = "🔶"
                break
            }
        }
    }

    // Cost -------------------
    if (guess.cost_memory !== null) {
        if (mysterycard.cost_memory === guess.cost_memory) {
            results.cost = "✅"
        } else if (mysterycard.cost_memory === null) {
            results.cost = "❌"
        } else if (guess.cost_memory < 0 || mysterycard.cost_memory < 0) {
            // one of them is -1 ("X")
            results.cost = "🔶"
        } else if (guess.cost_memory > mysterycard.cost_memory) {
            results.cost = "⬇️"
        } else {
            results.cost = "⬆️"
        }
    } else if (guess.cost_reserve !== null) {
        if (mysterycard.cost_reserve === guess.cost_reserve) {
            results.cost = "✅"
        } else if (mysterycard.cost_reserve === null) {
            results.cost = "❌"
        } else if (guess.cost_reserve < 0 || mysterycard.cost_reserve < 0) {
            // one of them is -1 ("X")
            results.cost = "🔶"
        } else if (guess.cost_reserve > mysterycard.cost_reserve) {
            results.cost = "⬇️"
        } else {
            results.cost = "⬆️"
        }
    } else {
        console.warn(`Unexpected cost case: ${guess.cost_memory}/${guess.cost_reserve} vs ${mysterycard.cost_memory}/${mysterycard.cost_reserve}`)
    }

    // Types ------------------
    //guess.types.sort()
    //mysterycard.types.sort()
    if (JSON.stringify(guess.types) === JSON.stringify(mysterycard.types)) {
        results.types = "✅"
    } else {
        for (const ty of guess.types) {
            if (mysterycard.types.includes(ty)) {
                results.types = "🔶"
                break
            }
        }
    }
    //guess.subtypes.sort()
    //mysterycard.subtypes.sort()
    if (JSON.stringify(guess.subtypes) === JSON.stringify(mysterycard.subtypes)) {
        results.subtypes = "✅"
    } else {
        for (const ty of guess.subtypes) {
            if (mysterycard.subtypes.includes(ty)) {
                results.subtypes = "🔶"
                break
            }
        }
    }
    
    // Stats (power, life, durability, speed) --------
    const guessstats = [guess.power, guess.life, guess.durability, guess.speed]
    const mysterycardstats = [mysterycard.power, mysterycard.life, mysterycard.durability, mysterycard.speed]
    if (JSON.stringify(guessstats) === JSON.stringify(mysterycardstats)) {
        results.stats = "✅"
        results.statresults = {}
        for (st of ["power","life","durability", "speed"]) {
            if (guess[st] !== null) {
                results.statresults[st] = "✅"
            }
        }
    } else {
        let statresults = {}
        for (const st of ["power","life","durability"]) {
            if (guess[st] === null) {
                if (mysterycard[st] === null) {
                    statresults[st] = null // Explicitly note the omitted stat
                } else {
                    // Don't note which stat they're missing
                }
            } else if (guess[st] === mysterycard[st]) {
                // Upgrade the overall result and note the correct stat
                results.stats = "🔶"
                statresults[st] = "✅"
            } else if (mysterycard[st] === null) {
                // Note the incorrect stat without upgrading
                statresults[st] = "❌"
            } else {
                // stats are both non-null so we can give a +/-
                if (guess[st] > mysterycard[st]) {
                    statresults[st] = "⬇️"
                } else {
                    statresults[st] = "⬆️"
                }
            }
        }
        if (guess.speed === null) {
            if (mysterycard.speed === null) {
                statresults["speed"] = null // Note the omitted stat
            } else {
                // Don't hint what they're missing
            }
        } else {
            if (guess.speed === mysterycard.speed) {
                // Upgrade the overall stats and note the match
                results.stats = "🔶"
                statresults["speed"] = "✅"
            // } else if (mysterycard.speed === null) {
            //     statresults["speed"] = "❌"
            } else {
                // It's fast (true) when it should be slow (false) or vice-versa
                statresults["speed"] = "❌"
                // If this doesn't also incorporate present-when-it-shouldn't-be
                // then maybe this could be "🔶"
            }
        }
        
        results.statresults = statresults
    }

    return {"card":guess, "results":results}
}

function addguess(card, results) {
    const gh = document.querySelector("#guesshistory")
    if (results === true) {
        gh.innerHTML = `
            <div class="guess correct">
                <h3> 🎉 Correct! </h3>
                <img src="https://api.gatcg.com${card.result_editions[0].image}" alt="${card.name}" width="250" height="350" class="card" />
            </div>
        ` + gh.innerHTML
        const nextpuz = document.querySelector("#next-puz")
        const guessbut = document.querySelector("#guess-butt")
        const hintbut = document.querySelector("#hint-plz")
        nextpuz.classList.remove("collapse")
        guessbut.disabled = true
        hintbut.disabled = true
        addprize()
        return
    }

    let elementdisplay = ""
    for (const el of card.elements) {
        elementdisplay += `<img alt="(${el.toLowerCase()})" src="https://cdn2.gatcg.com/i/elements/${el.toLowerCase()}.png" height="18" width="18" /><span class="element-name">${el.toLowerCase()}</span> `
    }

    let costdisplay = ""
    if (card.cost_memory !== null) {
        if (card.cost_memory === -1) {
            costdisplay = `<span class="memory-cost">X</span>`
        } else {
            costdisplay = `<span class="memory-cost">${card.cost_memory}</span>`
        }
    } else if (card.cost_reserve !== null) {
        if (card.cost_reserve === -1) {
            costdisplay = `<span class="reserve-cost">X</span>`
        } else {
            costdisplay = `<span class="reserve-cost">${card.cost_reserve}</span>`
        }
    }

    let statdisplay = ""
    for (const st in results.statresults) {
        if (results.statresults[st] !== null) {
            let statvalue = card[st]
            if (st === "speed") {
                if (card[st] === true) {
                    statvalue = "FAST"
                } else {
                    statvalue = "SLOW"
                }
            }
            statdisplay += `<div>${results.statresults[st]} <span class="stat ${st}">${st}</span> <span class="statvalue sv-${st} sv-${card[st]}">${statvalue}</span></div>`
        }
    }
    
    gh.innerHTML = `
        <dl class="guess">
            <dt>Guess</dt><dd>${card.name}</dd>
            <dt>Element(s)</dt><dd>${results.elements} ${elementdisplay}</dd>
            <dt>Cost</dt><dd>${results.cost} ${costdisplay}</dd>
            <dt>Types - <span class="subtypes">Subtypes</span></dt><dd class="card-types">${results.types} ${card.types.map((s)=>s.toLowerCase()).join(" ")} - <span class="subtypes">${results.subtypes} ${card.subtypes.map((s)=>s.toLowerCase()).join(" ")}</span></dd>
            <dt>Stats</dt><dd>${results.stats} (Overall)<br>${statdisplay}</dd>
        </dl>
    ` + gh.innerHTML
}

function choosecardauto() {
    // look up selected difficulty because browsers may keep a different
    // input selected when reloading
    const chosendiff = document.querySelector("#difficulty-select input:checked")
    if (chosendiff) {
        choosecard(chosendiff.value)
        return chosendiff.value
    } else {
        choosecard("easy")
        return "easy"
    }
}

async function choosecard(difficulty) {
    let rndi = Math.floor(Math.random() * ALLSLUGS[difficulty].length)
    let chosen_slug = ALLSLUGS[difficulty][rndi]
    let retries=0
    while (past_cards.includes(chosen_slug) && retries < 100) {
        let rndi = Math.floor(Math.random() * ALLSLUGS[difficulty].length)
        chosen_slug = ALLSLUGS[difficulty][rndi]
        retries += 1
    }
    if (retries >= 100) {
        console.log(`${retries} retries; resetting past_cards`)
        past_cards = []
    }
    mysterycard = await indexlookup(chosen_slug)
    // console.debug(`Chose answer: ${mysterycard.name}`)

}

function nextpuzzle(event) {
    const nextpuzbut = document.querySelector("#next-puz")
    const guessbut = document.querySelector("#guess-butt")
    const hintbut = document.querySelector("#hint-plz")
    nextpuzbut.classList.add("collapse")
    const diff = choosecardauto()
    guessbut.disabled = false
    hintbut.disabled = false
    const gh = document.querySelector("#guesshistory")
    gh.innerHTML=`<div class="choose-note">Playing on ${diff} difficulty.</div>`
    hints_given = []
    const ac = document.querySelector("#autocomplete")
    ac.innerHTML = ""
}

function advancedialog(event) {
    const nextbut = document.querySelector("#next-button")
    const dname = nextbut.dataset.dname
    const pagenum = parseInt(nextbut.dataset.nextpage)
    //console.debug(`Showing convo ${dname} page ${pagenum}`)

    if (pagenum >= ALLDIALOG[dname].length) {
        //console.debug(`Page ${pagenum} is past the end of ${dname}`)
        enddialog()
        if (dname == "startup") {
            window.localStorage.setItem("introseen", true)
        }
        return
    }
    const page = ALLDIALOG[dname][pagenum]
    nextbut.dataset.dname = dname
    nextbut.dataset.nextpage = pagenum+1
    showdialogpage(page)
}

function enddialog() {
    for (const el of document.querySelectorAll(".overlay-animated")) {
        el.classList.add("fadeOut")
        sleep(100).then(() => {
            el.classList.add("collapse")
            el.classList.remove("fadeOut")
        })
    }
    for (const el of document.querySelectorAll(".hint-record.collapse")) {
        el.classList.remove("collapse")
    }
}

async function showdialogpage(page) {
    const el = document.querySelector("#dialog-overlay")
    el.classList.remove("fadeIn")
    el.classList.add("fadeOut")
    await sleep(200)

    const dlg_spk = document.querySelector("#speaker-name")
    const dlg_text = document.querySelector("#dialog-text")
    const spimg = document.querySelector("#spoiler-img")
    for (const spkr_img of document.querySelectorAll(".speaker-image")) {
        if (spkr_img.alt == page.speaker) {
            spkr_img.classList.remove("collapse")
        } else {
            spkr_img.classList.add("collapse")
        }
    }
    
    if (page.spoiler) {
        spimg.src = page.spoiler
        spimg.classList.remove("collapse")
        dlg_text.innerHTML=""
        dlg_text.classList.add("collapse")
        dlg_spk.innerText=""
        dlg_spk.classList.add("collapse")
    } else {
        spimg.classList.add("collapse")
        dlg_spk.innerText = page.speaker
        dlg_spk.classList.remove("collapse")
        dlg_text.innerHTML=""
        for (const line of page.lines) {
            const p = document.createElement("p")
            p.innerText=line
            dlg_text.appendChild(p)
        }
        dlg_text.classList.remove("collapse")
    }
    // const el = document.querySelector("#dialog-overlay")
    el.classList.remove("collapse")
    el.classList.remove("fadeOut")
    el.classList.add("fadeIn")
}

function difficultychange(event) {
    if (event.target.checked) {
        //console.log(`Selected ${event.target.value} difficulty`)
        choosecard(event.target.value)
        nextpuzzle()
    }
}

function givehint(event) {
    if (hints_given.length >= ALLDIALOG["hint"].length) {
        showdialogpage(ALLDIALOG["nohints"][0])
        return
    }
    let rndi = Math.floor(Math.random() * ALLDIALOG["hint"].length)
    while (hints_given.includes(rndi)) {
        rndi = Math.floor(Math.random() * ALLDIALOG["hint"].length)
    }
    hints_given.push(rndi)
    const rawpage = ALLDIALOG["hint"][rndi]

    let need_subs = {}
    const parsedpage = {
        "speaker": ALLDIALOG["hint"][rndi].speaker,
        "lines": []
    }
    if (rawpage.needs.includes("__EDCOUNT__")) {
        need_subs["__EDCOUNT__"] = mysterycard.result_editions.length
    }
    if (rawpage.needs.includes("__ILLUST__")) {
        let rnd_ed = mysterycard.result_editions[Math.floor(Math.random() * mysterycard.result_editions.length)]
        need_subs["__ILLUST__"] = rnd_ed.illustrator
    }
    if (rawpage.needs.includes("__TEXT__")) {
        if (mysterycard.effect_raw === null) {
            need_subs["__TEXT__"] = "(Fooled you! It doesn't have text.)"
        } else {
            let card_text = mysterycard.effect_raw
            let cutoffs = [
                card_text.indexOf("."),
                card_text.indexOf("\n"),
                card_text.indexOf("(")
            ]
            cutoffs = cutoffs.filter((x) => x > 0)
            card_text = card_text.slice(0,Math.min(...cutoffs))
            card_text = card_text.replace(mysterycard.name, "███████████████")
            need_subs["__TEXT__"] = card_text
        }
    }
    if (rawpage.needs.includes("__SET__")) {
        let rnd_ed = mysterycard.result_editions[Math.floor(Math.random() * mysterycard.result_editions.length)]
        need_subs["__SET__"] = rnd_ed.set.prefix
    }
    if (rawpage.needs.includes("__FLAVOR__")) {
        if (mysterycard.flavor) {
            need_subs["__FLAVOR__"] = mysterycard.flavor
        } else {
            let rnd_ed = mysterycard.result_editions[Math.floor(Math.random() * mysterycard.result_editions.length)]
            if (rnd_ed.flavor === null) {
                need_subs["__FLAVOR__"] = "(Just kidding, it doesn't have flavor text.)"
            } else {
                need_subs["__FLAVOR__"] = rnd_ed.flavor
            }
        }
    }
    for (let line of rawpage.lines) {
        for (const need in need_subs) {
            line = line.replaceAll(need, need_subs[need])
        }
        parsedpage.lines.push(line)
    }

    const nextbut = document.querySelector("#next-button")
    nextbut.dataset.dname = "hint"
    nextbut.dataset.nextpage = 9999
    showdialogpage(parsedpage, true)

    let hinttext = `<div class="hint-record collapse"><span class="hint-label">Hint</span>`
    for (const line of parsedpage.lines) {
        hinttext = hinttext + `<p>${line}</p>`
    }
    hinttext = hinttext + "</div>"
    const gh = document.querySelector("#guesshistory")
    gh.innerHTML = hinttext + gh.innerHTML
}

function addprize() {
    victories += 1
    past_cards.push(mysterycard.slug)
    window.localStorage.setItem("victories", victories)
    updateprizing()
}

function updateprizing() {
    const pa = document.querySelector("#prize-area")
    const nextbut = document.querySelector("#next-button")
    if (victories >= 1 && !document.querySelector("#spoiler-btn-1")) {
        const spl1 = document.createElement("button")
        spl1.innerText = "Spoiler 1/3"
        spl1.id = "spoiler-btn-1"
        const spoilerseen = window.localStorage.getItem("seenspoiler1")
        if (!spoilerseen) {
            spl1.classList.add("tab-notif")
        }
        spl1.addEventListener("click", (evt) => {
            spl1.classList.remove("tab-notif")
            window.localStorage.setItem("seenspoiler1", true)
            nextbut.dataset.dname = "spoiler1"
            nextbut.dataset.nextpage = 0
            advancedialog()
            update_prizetab_notif()
        })
        pa.appendChild(spl1)
        spl1.classList.add("fadeInRel")
    }
    if (victories >= 2 && !document.querySelector("#spoiler-btn-2")) {
        const spl2 = document.createElement("button")
        spl2.innerText = "Spoiler 2/3"
        spl2.id = "spoiler-btn-2"
        const spoilerseen = window.localStorage.getItem("seenspoiler2")
        if (!spoilerseen) {
            spl2.classList.add("tab-notif")
        }
        spl2.addEventListener("click", (evt) => {
            spl2.classList.remove("tab-notif")
            window.localStorage.setItem("seenspoiler2", true)
            nextbut.dataset.dname = "spoiler2"
            nextbut.dataset.nextpage = 0
            advancedialog()
            update_prizetab_notif()
        })
        pa.appendChild(spl2)
        spl2.classList.add("fadeInRel")
    }
    if (victories >= 3 && !document.querySelector("#spoiler-btn-3")) {
        const spl3 = document.createElement("button")
        spl3.id = "spoiler-btn-3"
        spl3.innerText = "Spoiler 3/3"
        const spoilerseen = window.localStorage.getItem("seenspoiler3")
        if (!spoilerseen) {
            spl3.classList.add("tab-notif")
        }
        spl3.addEventListener("click", (evt) => {
            spl3.classList.remove("tab-notif")
            window.localStorage.setItem("seenspoiler3", true)
            nextbut.dataset.dname = "spoiler3"
            nextbut.dataset.nextpage = 0
            advancedialog()
            update_prizetab_notif()
        })
        pa.appendChild(spl3)
        spl3.classList.add("fadeInRel")
    }
    update_prizetab_notif()
}

function update_prizetab_notif() {
    const prizetab = document.querySelector("#tab-prizes")
    let notif_count = 0
    const splbuts = document.querySelectorAll("#prize-area > button")
    for (const prize of splbuts) {
        if (prize.classList.contains("tab-notif")) {
            notif_count += 1
        }
    }
    if (notif_count) {
        prizetab.classList.add("tab-notif")
    } else {
        prizetab.classList.remove("tab-notif")
    }
}

function selecttab(event) {
    const tabs = document.querySelectorAll("#ui-tabs-mobile button")
    for (const el of tabs) {
        if (el === event.target) {
            el.classList.add("active-tab")
            document.querySelector(el.dataset.tabfor).classList.add("mobile-active")
            document.querySelector(el.dataset.tabfor).classList.remove("mobile-inactive")
        } else {
            el.classList.remove("active-tab")
            document.querySelector(el.dataset.tabfor).classList.remove("mobile-active")
            document.querySelector(el.dataset.tabfor).classList.add("mobile-inactive")
        }
    }
}

function ready(callback) {
    if (document.readyState != "loading") callback()
    else document.addEventListener("DOMContentLoaded", callback)
}

ready(async () => {
    ALLSLUGS = await (await fetch("./slugs.json")).json()
    ALLDIALOG = await (await fetch("./dialog.json")).json()
    
    choosecardauto()

    const gf = document.querySelector("#guessform")
    gf.addEventListener("submit", pressguess)

    const diffbuttons = document.querySelectorAll("#difficulty-select input")
    for (const diffbut of diffbuttons) {
        diffbut.addEventListener("change", difficultychange)
    }

    const savedVictories = window.localStorage.getItem("victories")
    if (savedVictories) {
        victories = parseInt(savedVictories)
        updateprizing()
    }

    const closebut = document.querySelector("#close-dialog-button")
    closebut.addEventListener("click", enddialog)
    const hintbut = document.querySelector("#hint-plz")
    hintbut.addEventListener("click", givehint)
    const nextbut = document.querySelector("#next-button")
    nextbut.addEventListener("click", advancedialog)
    const nextpuzbut = document.querySelector("#next-puz")
    nextpuzbut.addEventListener("click", nextpuzzle)
    
    const mobiletabs = document.querySelectorAll("#ui-tabs-mobile button")
    for (const tab of mobiletabs) {
        tab.addEventListener("click", selecttab)
    }
    
    const introSeen = window.localStorage.getItem("introseen")
    if (!introSeen) {
        advancedialog()
    } else {
        enddialog()
    }

    const replayintrobut = document.querySelector("#replay-intro")
    replayintrobut.addEventListener("click", (event) => {
        nextbut.dataset.dname = "startup"
        nextbut.dataset.nextpage = 0
        advancedialog()
    })
})
