function show_delta_error(msg) {
    const errmsg = document.querySelector("#delta-err")
    errmsg.innerText = msg
    errmsg.classList.remove("collapse")
}

function cmp_card_o(a,b) {
    // requires carddb to be loaded separately
    if (carddb[a["card"]].rank == carddb[b["card"]].rank) {
        return 0
    } else if (carddb[a["card"]].rank > carddb[b["card"]].rank) {
        return 1
    }
    return -1
}

function normalize_dl(dlw) {
    if (!dlw || !dlw.decklist) { return }
    for (const card_o of dlw.decklist.material) {
        card_o["card"] = card_o["card"].toLowerCase()
    }
    for (const card_o of dlw.decklist.main) {
        card_o["card"] = card_o["card"].toLowerCase()
    }
    for (const card_o of dlw.decklist.sideboard) {
        card_o["card"] = card_o["card"].toLowerCase()
    }
    dlw.decklist.material.sort(cmp_card_o)
    dlw.decklist.main.sort(cmp_card_o)
    dlw.decklist.sideboard.sort(cmp_card_o)
    return dlw.decklist
}

async function get_dls() {
    const evt1_id = parseInt(document.querySelector("#delta-evt-1").value)
    const evt2_id = parseInt(document.querySelector("#delta-evt-2").value)
    const p1_id = parseInt(document.querySelector("#delta-p-1").value)
    const p2_id = parseInt(document.querySelector("#delta-p-2").value)
    if (!evt1_id || !evt2_id || !p1_id || !p2_id) {
        show_delta_error("Must supply valid Omni IDs for both events and both players")
        return
    }

    const e1_dls = await (await fetch(`https://api.gatcg.com/omnidex/events/${evt1_id}/decklists`)).json()
    let e2_dls
    if (evt1_id == evt2_id) {
        e2_dls = e1_dls
    } else {
        e2_dls = await (await fetch(`https://api.gatcg.com/omnidex/events/${evt2_id}/decklists`)).json()
    }
    if (!e1_dls || !e2_dls) {
        show_delta_error("Couldn't get one or both decklists.")
        return
    }

    set_names(evt1_id, p1_id, evt2_id, p2_id)

    const p1_dlw = e1_dls.find( (dlwrap) => dlwrap.player == p1_id )
    const p2_dlw = e2_dls.find( (dlwrap) => dlwrap.player == p2_id )
    return {
        "p1": normalize_dl(p1_dlw),
        "p2": normalize_dl(p2_dlw)
    }
}

async function set_names(evt1_id, p1_id, evt2_id, p2_id) {
    let p1name = await get_player(evt1_id, p1_id)
    let p2name = await get_player(evt2_id, p2_id)
    if (!p1name) {
        p1name = `Player #${p1_id} (Event ${evt1_id})`
    }
    if (!p2name) {
        p2name = `Player #${p2_id} (Event ${evt2_id})`
    }
    document.querySelector(".d1.name").innerText = p1name
    document.querySelector(".d2.name").innerText = p2name
}

async function get_player(eid, pid) {
    // TODO: test w/ teams
    const e = await (await fetch(`https://api.gatcg.com/omnidex/events/${eid}`)).json()
    const players = await (await fetch(`https://api.gatcg.com/omnidex/events/${eid}/players`)).json()

    const player = players.find( (p) => p.id == pid )
    if (!player) {
        show_delta_error(`Couldn't get info for player ${pid}`)
        return
    }

    return `${player.username} #${player.id} (${e.name})`
}

function reset_results() {
    const dv = document.querySelector("#delta-view")
    let els = Array.from(dv.querySelectorAll(".name"))
    els = els.concat(Array.from(dv.querySelectorAll(".cardcount")))
    els = els.concat(Array.from(dv.querySelectorAll(".deck_gfx")))
    for (const el of els) {
        el.innerHTML = ""
    }
    const errmsg = document.querySelector("#delta-err")
    errmsg.innerHTML = ""
    errmsg.classList.add("collapse")
}

function show_loader() {
    document.querySelector("#delta-loader").classList.remove("collapse")
    document.querySelector("#delta-go").disabled = true
}
function hide_loader() {
    document.querySelector("#delta-loader").classList.add("collapse")
    document.querySelector("#delta-go").disabled = false
}

function cardimg(card_o) {
    // requires carddb
    const el = document.createElement("div")
    el.classList.add("cardimg")
    el.innerHTML = `
    <img src="${carddb[card_o.card].img}" alt="${card_o.card}" />
    <span class="quant">${card_o.quantity}</span>
    `
    if (card_o.quantity.slice(0,1) == "-") {
        el.classList.add("minus")
    }
    if (card_o.subquantity) {
        const sq = document.createElement("span")
        sq.innerText = card_o.subquantity
        sq.classList.add("subquant")
        el.querySelector(".quant").appendChild(sq)
    }
    return el
}

function calc_delta(lista, listb) {
    const deltaa = []
    const deltab = []
    let i = 0
    let j = 0
    let imax = lista.length
    let jmax = listb.length
    while (i < imax && j < jmax) {
        const a = lista[i]
        const b = listb[j]
        if (carddb[a.card].rank < carddb[b.card].rank) {
            deltaa.push({
                "card": a.card,
                "quantity": `-${a.quantity}`
            })
            i++
        } else if (carddb[a.card].rank > carddb[b.card].rank) {
            deltab.push({
                "card": b.card,
                "quantity": `+${b.quantity}`
            })
            j++
        } else {
            // ranks are even, so cards are same. check quantity
            if (a.quantity > b.quantity) {
                delta = a.quantity - b.quantity
                deltaa.push({
                    "card": a.card,
                    "quantity": `-${delta}`,
                    "subquantity": `from ${a.quantity}`
                })
            } else if (a.quantity < b.quantity) {
                delta = b.quantity - a.quantity
                deltab.push({
                    "card": a.card,
                    "quantity": `+${delta}`,
                    "subquantity": `to ${b.quantity}`
                })
            }
            i++; j++
        }
    }
    while (i < imax) {
        const a = lista[i]
        deltaa.push({
            "card": a.card,
            "quantity": `-${a.quantity}`
        })
        i++
    }
    while (j < jmax) {
        const b = listb[j]
        deltab.push({
            "card": b.card,
            "quantity": `+${b.quantity}`
        })
        j++
    }
    return [deltaa, deltab]
}

async function glimpse_delta() {
    reset_results()
    show_loader()
    const dls = await get_dls()
    if (!dls) {
        show_delta_error("Couldn't get both decklists from Omnidex")
        hide_loader()
        return
    }
    const {p1, p2} = dls
    if (!p1 || !p2) {
        show_delta_error("Couldn't get one of the decklists from Omnidex")
        hide_loader()
        return
    }
    
    // Calculate decklist deltas per section
    const [p1matd, p2matd] = calc_delta(p1.material, p2.material)
    const d1mat = document.querySelector(".d1.mat-deck .deck_gfx")
    if (!(p1matd.length + p2matd.length)) {
        d1mat.innerHTML = '<p class="explanation">(Material decks are identical!)</p>'
    } else {
        for (const card_o of p1matd) {
            d1mat.appendChild(cardimg(card_o))
        }
        const d2mat = document.querySelector(".d2.mat-deck .deck_gfx")
        for (const card_o of p2matd) {
            d2mat.appendChild(cardimg(card_o))
        }
    }

    const [p1maind, p2maind] = calc_delta(p1.main, p2.main)
    const d1main = document.querySelector(".d1.maindeck .deck_gfx")
    if (!(p1maind.length + p2maind.length)) {
        d1main.innerHTML = '<p class="explanation">(Maindecks are identical!)</p>'
    } else {
        for (const card_o of p1maind) {
            d1main.appendChild(cardimg(card_o))
        }
        const d2main = document.querySelector(".d2.maindeck .deck_gfx")
        for (const card_o of p2maind) {
            d2main.appendChild(cardimg(card_o))
        }
    }

    const [p1sided, p2sided] = calc_delta(p1.sideboard, p2.sideboard)
    const d1side = document.querySelector(".d1.sideboard .deck_gfx")
    if (!(p1sided.length + p2sided.length)) {
        d1side.innerHTML = '<p class="explanation">(Sideboards are identical!)</p>'
    } else {
        for (const card_o of p1sided) {
            d1side.appendChild(cardimg(card_o))
        }
        const d2side = document.querySelector(".d2.sideboard .deck_gfx")
        for (const card_o of p2sided) {
            d2side.appendChild(cardimg(card_o))
        }
    }
    hide_loader()
}

document.querySelector(".decklist-delta").addEventListener("submit", (evt) => {
    evt.preventDefault()
    glimpse_delta()
})

ready( () => {
    const params = new URLSearchParams(window.location.search)
    let filled = 0
    for (const [key, val] of params) {
        if (key == "p1") {
            try {
                const p1 = parseInt(val)
                document.querySelector("#delta-p-1").value = p1
                filled++
            } catch (err) {
                console.error(err)
                filled--
            }
        } else if (key == "p2") {
            try {
                const p2 = parseInt(val)
                document.querySelector("#delta-p-2").value = p2
                filled++
            } catch (err) {
                console.error(err)
                filled--
            }
        } else if (key == "e1") {
            try {
                const e1 = parseInt(val)
                document.querySelector("#delta-evt-1").value = e1
                filled++
            } catch (err) {
                console.error(err)
                filled--
            }
        } else if (key == "e2") {
            try {
                const e2 = parseInt(val)
                document.querySelector("#delta-evt-2").value = e2
                filled++
            } catch (err) {
                console.error(err)
                filled--
            }
        }
    }
    if (filled == 4) {
        glimpse_delta()
    }
})
