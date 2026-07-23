# Sprint-Refine skill

The sprint-refine skill converts a list of hand-written tasks (passed as Markdown bullet points)
into detailed task descriptions with estimated story points, breaking down any complex tasks into
smaller, more refined tasks that can be easily understood and implemented by anyone on the team or by an AI agent.

## Why use this skill

I personally don't fully trust my ability to break down a number of big tasks into small enough tasks that we can be confident
each one is detailed enough to be easily implemented without any unexpected discoveries.

Usually, the larger the sprint plan, the more likely I am to miss the details of a few specific tasks and only realize
I underestimated a task or group of tasks once I or someone on the team is already working on it, which can cause unpredictable
changes to the original level-of-effort estimates for that task and for the sprint as a whole.

That is why I always prefer to estimate sprint tasks in a group meeting with the whole team, so each person can share any doubts
they have and do their own risk and complexity evaluation, greatly reducing the odds of tasks being grossly underestimated.

But this is an expensive process that requires a lot of time from multiple software engineers.

## How this skill works

This skill uses AI agents to replicate a sprint-planning process I would normally run with a team of software engineers,
doing several rounds of evaluation on each task, where each agent estimates the level of effort of each task
in terms of Story Points. If the story points suggested by different evaluators diverge significantly,
it is an indicator that we might be missing some important detail about that task and that we need to discuss and
detail it further.

Any task whose estimate lands above 3 SP is also treated as a sign that the task needs to be broken down into
smaller pieces, which the AI does for you.

Furthermore, each task needs to be carefully reviewed and the codebase checked to make sure everything is aligned
and makes sense. This skill also includes processes for these validations. They are:

1. Checking that any claims about the code or external technologies match existing sources (docs/code)
2. Checking that each task is not inadvertently proposing to duplicate logic that already exists in the codebase
3. Checking that the output text is readable and comprehensible
4. Checking the proposed solution matches good UX practices

## Using this skill:

### The very first sprint

You can ask your agent to start it, or you can start it manually by first creating a sprint draft file
(in Markdown) and then calling the command with:

/sprint-refine <path-to-sprint-draft.md> <any extra details about what you need>

The agent will start the process and provide a few different outputs:

1. Right at the start it will ask you questions about the sprint if it cannot answer by itself
2. It will produce a refined version of the sprint as a separate file with a `-refined.md` suffix

The output sprint will be formatted as Markdown with the following sections:

1. Goals
2. Tasks
3. Stretch — optional tasks you might want to include on the sprint but that
   will not be required to be finished before the end of the sprint.
4. Backlog
5. Open Questions

After obtaining the refined version of the sprint, review it and answer the Open Questions if there are any.

Any problems you find you can write down by just adding a comment prefixed with `FIX:` anywhere on
the sprint.

You might also want to include `FIX:` instructions anywhere in the sprint body asking a task to be
moved up or down the priority list, or moved to the Stretch or Backlog section.

You may then call the same skill again passing the path of the refined and reviewed sprint file,
it will read all the answers to the open questions and all the `FIX` comments and act on them
updating tasks accordingly following the same vote and breakdown and refinement process.

When you are satisfied you should be able to publish the sprint.

### Future sprints

For future sprints you might want to start from the old sprint and just ask the skill to double check
that all tasks marked as done are indeed implemented and remove them from the sprint if they are.

You can also use the backlog as the source for new tasks just moving them up to create the draft of the next sprint.
