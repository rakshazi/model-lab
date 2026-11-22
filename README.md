# model-lab: your skills are worse than they could be

> Details, explanations, and story with bad jokes will be published later on [rakshazi.me/blog](https://rakshazi.me/blog/) and linked here. In the meantime, check what's already there (and oh boy, there is *a lot* of unhinged stuff, I promise).

I use coding agents, and also use popular agent skills, but sometimes (turns out, a lot), I need to write my own skills,
usually to give domain-specific knowledge or establish a proper procedure when doing stuff.

How would you write a skill for a task? You ask your agent to do the task, provide feedback on the results, iterate, and when finished, you ask it to write a skill, so next time such task will be easier, right?

Yeah, turns out such skills are pretty bad. [SkillsBench](https://arxiv.org/abs/2602.12670) put a number on it: skills curated by a human add 16.6 points to the pass rate, while skills the agent wrote for itself land 8 to 11.5 points *below* having no skill at all. [SkillAxe](https://arxiv.org/abs/2606.10546) found the same from the other side: LLM-authored skills give no measurable gain until an evaluation loop refines them. And the self-improving crowd, all the way up to [Harness²](https://arxiv.org/abs/2610.14224), gets its gains from that same place: propose, probe, measure, keep what survived.

How to fix that? Welcome to model-lab!

History: I asked big "it is so dangerous" model to write a skill, the results of the skill (in next runs) were pretty bad (I expected faster and cleaner execution of the task), so I got an idea: iterate skill on small models: 300-500b, 27b, and 4b params, and document what worked and what didn't. That's how model-lab was born: literally README.md file, where each line is a lesson learned.

Now, what model-lab *is*? A skill to write skills (with generalized lessons from previous iterations, up to the original README.md), with agent-specific quirks, scaffolding to spin up a test stand for verification, and instructions to iterate and improve based on the proven ~~results~~ failures.

How it works? Install the skill, and then ask your agent to write a skill for a task, and then let it cook: test stands, n=3 or n=5 runs per iteration, the result: a skill that actually works. Bonus: that skill will also work on smaller models, so proprietary providers' enjoyers can use Haiku/Luna/%name-other-dumb-and-cheap-model% for doing real work and costing them less than a cup of coffee for a big task.

Examples of skills written with model-lab: [write AGENTS.md](https://github.com/rakshazi/write-agentsmd) (procedure skill), [krea2-prompting](https://github.com/rakshazi/krea2-prompting) (domain knowledge skill). Plus, planning skill (procedure, later converted to [pi extension](https://github.com/rakshazi/pi-extensions/tree/main/plan-mode)), spec skill (procedure, described/shared in [You Don't Need a %Frontier LLM%](https://rakshazi.me/blog/you-dont-need-frontier-llm/#a-smaller-model-is-dumb-and-doesnt-understand-what-i-want)), etc. (unfortunately, not all stuff can be shared publicly, because I mostly use model-lab for internal domain knowledge and procedures).
