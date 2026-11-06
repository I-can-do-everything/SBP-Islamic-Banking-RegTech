# LI-19. A compliance tool in signal red, without making everything look like a breach

**Week 6, Monday** | Milestone: M7 | Images: `assets/screens/00-landing-hero.png`, then `assets/screens/05-results.png`

---

I gave a compliance tool a bright red brand. In compliance, red means "breach".

That sounds like a mistake. Here is how Daleel makes it work.

One red cannot do every job. #ff2c2c on white is only 3.7 to 1 contrast, below the 4.5 to 1 that small text needs to be readable. So the colour is split into roles:

🔴 The exact red, #ff2c2c, is kept for big shapes: the star mark, the underline in the headline, a thin bar at the top.
🔴 A deeper red, #d41c1c, is used for text and buttons, at 5.3 to 1.
🌹 Breaches get their own crimson rose, a different red, and never appear without an icon and the word "Breach".
🟢 Anything finished or approved stays green. The first version of the progress bar showed red ticks for completed steps, which read as failure. That was fixed.

I checked every colour pair with the WCAG formula, not by eye. Two failed: a pale grey used for labels, and white text on the bright red band at the bottom of the landing page. Both were changed.

The landing page follows the same idea as the product: it opens with a real figure from the demo and the evidence behind it, instead of a slogan.

Live demo and code in the comments. Synthetic data only.

#ProductDesign #Accessibility #UXDesign #RegTech #FinTech
