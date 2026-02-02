# Creation of a new openclaw helm chart from previous source prompt improvement

## Instructions 

Here is a tentative prompt to direct claude code to create analogous new helm
chart based on the recent source.  Consider the prompt and improve it to make
it best direct Claude code or similar reasoning LLM to achieve creation of a
new openclaw helm chart that deploys openclaw 

## Tentative Prompt

The directories openclaw and clawdbot are 2 directories containing the source
for helm charts.  They are ment to deploy softwre from a project openclaw
(see https://github.com/openclaw/openclaw). The clawdbot directory was created
to deploy when the project as named clawdbot. The openclaw directory is a newly
created directory structure using helm create openclaw.  The directory upstream
contains the source to create the openclaw container and deploy it using
docker-compose and the upstream/doc/install directory contains instructions on
how to deploy openclaw which includes the necessary environment that needs to
be constructed.  Read the source contained in clawdbot and upstream to
understand how openclaw is deployed and modify the source in the openclaw
directory to correspond to a correct and thorough helm package to deploy
openclaw.  Consider what tests are necessary to verify correctness. If
anything is unclear ask clarifying questions.
