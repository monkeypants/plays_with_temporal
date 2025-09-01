# So based on the [discussion on this issues](https://github.com/pyx-industries/julee-orchestrator/issues/1)
# an assembly should, I believe, have the following attributes:
#  - A unique Id
#  - A name (eg. "meeting minutes")
#  - An applicability (a text description of what this assembly applies to, used by the
#    knowledge service lookup/query to link assemblies to documents)
#  - A jinja2 template (it's still not clear to me why this should be the source of truth for
#    extractors). As I mentioned on the issue, I wonder if this should be sub templates
#    (includes) where each include has a one-one relationship with an extractor (such as
#    "action-items", or "agenda topic", or "agenda"). Agenda topic is an interesting one, where
#    either it needs to be run multiple times, or it runs once and returns a list?). I do
#    think that the template should not be part of the assembly, but a separate rendering of
#    the assembly.
#  - Instead of a jinja2 template, a list of top-level data chunks / extractors (eg. for the
#    meeting minutes example, it might be document metadata, agenda items, action items and
#    next meeting details, where agenda items is composed of smaller data chunks / extractors)
# Either way, it appears there's a 1:M relationship between an assembly and extractor, whether
# that's through included sub-templates or the context variables themselves. And each extractor
# sounds like it extracts a unit of structured data (a "chunk"? using ragflow terminology?),
# which can be composed together to form the document..
# Document author. Document creation date.
