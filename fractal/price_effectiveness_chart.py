

def svg_price_effectiveness_chart(decks,dotsize=1.5):
    """
    Given a list of decks, return an SVG scatterplot of their cost effectiveness
    where price is on the X axis and score (as a % of total points) is on the Y
    axis. Not currently used.
    """
    xoff = 50
    yoff = 20
    s = f'<svg viewBox="0 0 1100 1100" xmlns="http://www.w3.org/2000/svg">\n<rect x="{xoff}" y="{yoff\
+1001}" width="1000" height="1" fill="transparent" stroke="black" /><rect x="{xoff}" y="{yoff}" width="1"\
 height="1000" fill="transparent" stroke="black" />\n'
    pricemax = max([d.price_num for d in decks])
    for y in range(11):
        yp = f"{y*10}%"
        y = (1000 - (y*100)) + yoff
        s += f'<text x="0" y="{y}">{yp}</text>\n'
    for x in range(11):
        xp = f"${x * .1 * pricemax : .2f}"
        x = (x*100) + xoff
        s += f'<text x="{x}" y="{yoff+yoff+1000}">{xp}</text>\n'
    for d in decks:
        if d.els == ["Fire"]:
            fill = "rgba(200,0,0,.5)"
        elif d.els == ["Water"]:
            fill = "rgba(0,0,200,.5)"
        elif d.els == ["Wind"]:
            fill = "rgba(0,128,0,.5)"
        else:
            fill = "rgba(0,0,0,.5)"
        cx = 1000 * (d.price_num / pricemax) + xoff
        if hasattr(d.entrant, "team"):
            score_pct = (d.entrant.event.teams[d.entrant.team.lower()].score /
                         d.entrant.event.rounds * 3)
        else:
            score_pct = d.entrant.score / (d.entrant.event.rounds * 3)
        cy = yoff + 1000 - (1000 * score_pct)
        s += f'<circle cx="{cx}" cy="{cy}" r="{dotsize}" fill="{fill}" />\n'
    s += '</svg>\n'
    return s
