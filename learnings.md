# Learnings

Everything I learn from building on AWS with Claude Code. Not just what worked — why it worked, what broke first, and what I'd do differently.

---

## AWS Account Setup (2026-04-15)

### Getting back into an old AWS account
- Signed in as root user, had to reset password since it had been years
- Account was clean — no surprise resources running, no accumulated charges
- First thing to do: check Billing dashboard across all regions for zombie resources

### IAM user for CLI
- Created IAM user `kev` with AdministratorAccess — fine for personal learning, would never do this at work
- Created access key, ran `aws configure` locally
- Default region: us-east-1 (most services available, cheapest)
- AWS CLI was already installed via homebrew (`aws-cli/2.21.3`)
- Verified with `aws sts get-caller-identity` — shows account ID, user ARN

### EC2 instance launch (all via CLI)
- **Key pair**: `aws ec2 create-key-pair` — saves the .pem file locally at `~/.ssh/kev-aws-learning.pem`, must `chmod 400` immediately
- **Security group**: Created `aws-learning-sg`, opened ports 22 (SSH), 80 (HTTP), 443 (HTTPS) to 0.0.0.0/0
- **AMI selection**: Used `aws ec2 describe-images` with filters for Ubuntu 24.04 ARM64 — sort by CreationDate and grab the latest
- **Instance type**: `t4g.micro` — ARM/Graviton processor, free tier eligible for 750 hrs/month in first 12 months
- **Storage**: 20 GB gp3 (default is 8 GB which fills up fast with Python venvs)
- **SSH worked on second try** — first attempt got "Connection refused" because sshd hadn't started yet. EC2 "running" state doesn't mean SSH is ready. Wait ~15-30 seconds after instance enters "running" state.

### What I'd do differently
- Could attach an Elastic IP so the address doesn't change on stop/start — haven't done this yet, will add when it becomes annoying
- Should set up a billing alarm/budget immediately (haven't done this yet either)

---

## Claude Code Workflow Learnings

### Using Claude Code to manage remote servers
- Claude Code runs locally on my Mac but can SSH into the EC2 instance to run commands
- Pattern: Claude runs `ssh -i key ubuntu@ip "command"` to execute things on the server
- This means Claude Code can set up the server, install packages, edit files, and deploy — all from my local terminal

### PRD-driven development
- Write a PRD first, then hand it to Claude Code
- At work this produced 4 experiments in a single session
- The PRD acts as both documentation and instruction set
- CLAUDE.md is the quick-reference version that Claude reads on every conversation start

(More learnings will be added as experiments are built...)
