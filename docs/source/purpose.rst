Purpose
=======

This codebase exists to explore and demonstrate
approaches to incorporating non-deterministic components
into a transparent and accountable process.
It's about enabling algorithmic due diligence
so that we can place measured trust in digital products.

This requires one of two things, either:

1) We place faith in the party who produced a digital product; or
2) We understand and scrutenise how it was produced.

This codebase is concerned with the latter.
We want to incorporate non-deterministic activities
into a transparent and accountable process,
so we can apply "algorithmic due diligence"
to assess certain claims about quality.

To do this, we are building non-agentic orchestrations.
Processes where deterministic workflows
combine potentially non-deterministic activities.
These are decentralised systems - the activities are performed
by different identities to the workflow itself.

So the orchestrator (workflow) is deterministic,
transparent, and accountable.
And the activities essentially are separate inputs from 3rd parties.


This is not an Agent
--------------------

Some of the most useful AI implementations are "Agentic",
which is an overloaded word but I'll use it to mean that the AI
applies tools in a loop to achieve a goal.
So the process that creates the product is non-deterministic,
because AI is used to figure out how to achieve the goal.
It won't always go about things in the same way.

Non-deterministic processes have disadvantages and advantages.
They can be difficult to understand, predict, and control.
But they can also be resilient and operate more effectively in chaotic and dynamic circumstances.
They can be more intelligent, they can work better.

Older definitions of agents, from late in the AI winter (1980s),
were focussed on moving beyond the limits of symbolic reasoning.
They looked at "situated action", where something can't see the whole picture
but it has to decide and act anyhow.
Many real world situations are like this,
sometimes it's called "the fog of war",
sometimes it's just so normal that we don't notice.

Imperfect information and non-deterministic behaviour are indistinguishable
from the perspective of something that needs to make a decision.

The AI research of this time was an early form of complexity science.
It was looking at how complex phenomena emerged from relatively simple rules.
What we are doing in this codebase is to apply the Temporal framework
to implement deterministic workflows,
which is a practical and robust way to implement simple deterministic rules.

We are using Temporal to orchestrate these rules and guarantee
that if they can be run, they eventually are.
Furthermore, the mechanism that ensures the rules are run
also keeps a record as it proceeds.
So we have a log of what did happened,
and a set of rules about what should happen,
and we can see for ourselves that they match.

This is very different to allowing AI to decide what should happen.
Our orchestrations are deliberately hard-coded,
because we want the ability to study and iteratively refine them.
We are essentially pushing the non-deterministic behavior down
into the orchestrated activities, rather than the orchestrator itself.

Those activities are operated by separate entities.
So the orchestrator has qualities of transparency, auditability, etc.
that allows us to trust its output using "method 2"
(We understand and scrutinise how it was produced),
with the caveat that we don't necessarily trust its inputs.
The orchestrator is accountable for the things that it controls,
but it doesn't control the activities that contributed to it.
It has delegated partial responsibility for the things outside its control.

We may choose "method 1" (place faith in the party who produced it)
or "method 2" (understand and scrutinise) for each of the input activities.

The orchestration is the beginning of a "trust graph",
that links up "understand and scrutinise" subgraphs
along with "trust the producer" nodes.
Where the root orchestration delegates to a "method 2" node
(deterministic workflow activity),
the process of algorithmic due diligence can extend into
the evidence of how that node performed its work. 
This process can continue recursively.
Where the graph encounters a non-deterministic activity,
the provenance graph stops and we are left with
an assessment of the producer themselves,
rather than the process of production.
This is not necessarily the boundary of the situation.
We may have internal policies about who to trust in what ways,
or we may dynamically assess other information about the party who performed the action.
These might include private information,
such as an assessment of their performance in other orchestrations,
or exogenous information (public or privileged access)
such as credentials, accreditation, licences or reputation sources.

The overall risk-based decision making can use patterns like
"additive trust when evidence corroborates",
allowing orchestrations to be designed in a way that deterministically assembles
the information that is required to make a particular operational decision.


The Architecture is Important
-----------------------------

This code is organised in a very particular way (:doc:`clean_architecture`).
This is deliberate, because we have a symbolic reasoning kernel
(domain models and usecases) that is decoupled from external services.
It is a pragmatic way for developers to be really clear
and explicit about "what should happen" (the usecase layer),
and what that actually means (the entity layer),
and remain loosely coupled from the activities
(interactions with 3rd parties).

The current implementation is an attempt to do a few useful things
while producing a trust-graph that can be
subject to algorithmic due diligence.
But the goal is to learn how to write code with these qualities more generally.
This is another benefit of clean architecture layering,
we should be able to add new processes and domain models.
Clean Architecture advocation often focusses on the ability to substitute
implementation layer components.
But it works the other way as well.
