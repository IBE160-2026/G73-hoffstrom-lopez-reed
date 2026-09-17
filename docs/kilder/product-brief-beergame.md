# Product Brief: Beer Game — Interactive Supply Chain Management Simulation Platform

## Executive Summary

The Beer Game is an AI-enhanced web platform that turns MIT's classic supply chain simulation into a complete teaching and learning environment. Learners play a distribution game — as retailer, wholesaler, distributor, or factory — where every ordering decision ripples through the chain, and the bullwhip effect emerges from their own choices rather than from a lecture slide. The platform supports single-player games against AI-controlled partners, multiplayer games with human or AI participants, and full classroom deployments where an educator configures one common scenario for an entire cohort.

The problem is not that the Beer Game lacks value — it is that running it well is expensive and laborious. Physical versions consume hours of class time and produce data that has to be tallied by hand. Existing digital versions are proprietary, costly, or thin on the analytics and assessment features educators actually need. Individual learners and professionals have essentially no accessible option at all. This platform closes that gap: automated student allocation, real-time monitoring with intervention controls, AI-generated summaries that explain what happened in each learner's own game, AI-generated and AI-assessed comprehension questions, and class-wide analytics with exportable reports.

The timing matters. LLM APIs now make two previously impractical things routine: credible AI opponents that let a single learner play a four-role game alone, and personalised assessment and feedback at cohort scale without adding grading hours. Combined with a managed backend stack (Supabase, Stripe, Vercel) and AI-assisted development, an MVP that would once have been a multi-month build is achievable within a 5-week course-length timeline.

## The Problem

Supply chain dynamics are counterintuitive. Students can recite the definition of the bullwhip effect and still fail to recognise it in their own ordering behaviour. The Beer Game solves this by making them feel it — but the delivery mechanism is where it breaks down.

For educators, running the game means either the physical version — hours of setup, four students locked to one chain, manual data collection, and no reliable way to compare performance across groups — or a commercial digital tool priced for corporate training that offers little beyond the game loop itself. Neither gives an educator what they need after the game ends: evidence that learning occurred. Assessment questions have to be written by hand, graded by hand, and reconciled against each student's individual game data by hand. For a class of forty, that is hours of work per run, which in practice means the game gets played once a semester, if at all.

For students, the constraint is coordination. A four-role game requires three other people available at the same time. Miss a session and there is no way to catch up. When the game does finish, the takeaway is often a chart the instructor shows to the whole room, not an explanation of what *this* student's decisions caused.

For supply chain professionals and self-directed learners, there is essentially no entry point at all. The educational value is locked behind a classroom they are not enrolled in.

## The Solution

A web-based platform with two connected surfaces: a player experience and an educator platform.

**For players.** A learner registers and starts a game in minutes — single-player against AI partners, or multiplayer with a mix of human and AI roles. Game parameters (duration, cost structure, lead times, difficulty, whether communication between roles is visible) are configurable. During play, an interactive dashboard shows inventory, backorders, incoming and outgoing orders, shipments, accumulated costs, and the current week, with live charts tracking each of those over time. Order placement happens in the same view. Game state persists, so a session can be interrupted and resumed. On completion, an AI-generated summary explains that player's performance: what their ordering pattern was, where amplification entered the chain, what it cost, and what to do differently — accompanied by a bullwhip visualisation drawn from their own data.

**For educators.** A subscribing teacher creates a class, bulk-registers students, and allocates them to games either automatically or by hand. All students in a class run a common configuration, which makes cross-group comparison meaningful. A live monitoring dashboard shows every active session and each student's progress, with controls to pause or reset a game, or to remove an absent student and replace them with an AI player so the remaining group is not blocked. Broadcast and individual messaging keep the cohort coordinated. After play, the platform generates assessment questions tailored to each student's game — multiple choice, short and long text, numeric — assesses the responses, applies weighted scoring against a passing threshold, and returns feedback. The analytics dashboard covers class-wide metrics, individual reports, bullwhip analysis, and exportable results.

Under the hood: Next.js and TypeScript on the front end, FastAPI and Supabase (PostgreSQL, Auth, Realtime, row-level security) on the back end, an LLM API for AI players and assessment, Stripe for subscriptions, SendGrid for notifications.

## What Makes This Different

The honest differentiators are these:

**AI opponents remove the coordination barrier.** Most existing implementations require a full human group. Filling roles with LLM-driven players makes solo play a first-class mode rather than a degraded one, and lets an educator keep a session running when a student does not show up.

**Assessment is generated from the learner's own game.** Questions are grounded in what that student actually did — their orders, their inventory swings, their costs — rather than being generic recall items. This is the feature that converts the game from an activity into something an educator can grade, and it is the main source of the claimed time saving.

**It is built for a class, not just a session.** Bulk registration, automated allocation, a shared configuration across the cohort, live intervention controls, and comparative analytics are the parts that make repeat use practical. Competing tools tend to treat the classroom as an afterthought.

**Accessible pricing and open access to the single-player mode.** Individual learners and professionals can use the platform without an institutional purchase.

What this is *not*: there is no proprietary algorithm or defensible technical moat here. The simulation logic is well documented and public. The advantage is execution — assembling AI opponents, AI assessment, and classroom operations into one product cheap enough to adopt — and that advantage holds only for as long as it takes someone else to build the same thing.

## Who This Serves

**Students** in supply chain, operations, and business administration courses. They need to complete an assigned game without depending on classmates' schedules, understand what their own decisions caused, and get a grade that reflects their comprehension. Success for them is finishing the game, recognising the bullwhip effect in their own data, and passing the assessment.

**Educators** teaching operations and supply chain management. They need to deploy the game to an entire class with minimal setup, watch it run, intervene when it stalls, and come away with defensible assessment data. Success for them is running the game more than once a term because the overhead no longer makes it prohibitive — the target is 5+ hours saved per class run.

**Supply chain professionals and individual learners** who want the experience without enrolling in a course. They need a low-friction entry point: guest access, a simplified setup, a game that can be played in one sitting. Success is understanding a dynamic they had heard described but never observed.

**Secondary users:** corporate training coordinators running internal workshops, and researchers who want structured decision data from repeated play.

## Success Criteria

**Functional.** A player can complete a full game end to end. A teacher can create a class, register students, allocate games, monitor them live, and export results. AI-generated assessment questions are accurate and grounded in the learner's game data. The bullwhip visualisation is clear enough that learners identify the effect without prompting. Payments process successfully.

**Technical.** 99% uptime. Game state persists reliably across interruptions. 100 concurrent sessions supported. Page load under 3 seconds; game state updates under 500ms; database queries under 200ms at the 95th percentile. Test coverage above 80%.

**Educational.** 80%+ of students show measurable improvement in understanding between pre- and post-game assessment. Students identify the bullwhip effect in their own data. Educators report 5+ hours saved per class run versus their previous method.

**Business.** 10+ paying teacher subscriptions within three months of launch. An average of 2+ games played per individual learner. 70%+ conversion from free trial to paid subscription.

## Scope

**In for v1.**

Player side: registration and authentication; single-player mode with AI partners; multiplayer with human or AI participants; configurable game parameters (duration, costs, lead times, difficulty, communication visibility); the real-time game dashboard with order placement; AI-controlled opponents; live charts for inventory, orders, and costs; AI-generated completion summary with bullwhip visualisation; persistent game state; responsive layout down to 768px (desktop, laptop, tablet).

Educator side: institutional-email registration; subscription billing via Stripe; class creation and management with bulk student registration; automated and manual game allocation; a shared configuration per class; live monitoring with pause, reset, and replace-with-AI controls; AI-generated and AI-assessed questions across multiple question types with weighted scoring and a pass threshold; broadcast and individual messaging; the analytics dashboard with individual and class-level reporting, bullwhip analysis, and CSV/PDF export; completion status management.

**Explicitly out of v1.**

In-game chat. Advanced scenario customisation (variable demand patterns, custom cost models, alternative product types, non-standard chain topologies). Gamification — leaderboards, achievements, rankings. Predictive analytics and decision-pattern analysis. A native mobile app, and phone-width layouts below 768px. LMS integration with Canvas or Moodle. Social sharing. Replay and strategy-analysis tooling. Collaborative team mode, where multiple students share one role. Multilingual support.

These are deferred, not rejected — several are the natural first additions after launch.

## Vision

The near-term goal is straightforward: become the default way the Beer Game is taught, because it is the version that is free to try, works with one student or forty, and produces a grade at the end.

Beyond that, the simulation is one instance of a general pattern — a dynamic system where individual decisions produce counterintuitive aggregate behaviour, and where understanding comes from playing rather than reading. The same platform mechanics (configurable scenarios, AI-filled roles, decision logging, AI-generated assessment grounded in what the learner actually did) generalise to newsvendor problems, capacity and queueing dynamics, procurement negotiation, and other operations topics that are hard to teach from a textbook. In two to three years the ambition is a library of such simulations under one classroom platform, with LMS integration so allocation and grades flow into the systems institutions already run.

The accumulated decision data is a second, quieter opportunity. Thousands of logged games across varied configurations form a research dataset on how people actually behave under information delay and demand uncertainty — useful to researchers, and useful for making the AI opponents behave less like optimisers and more like the humans learners will eventually work alongside.
