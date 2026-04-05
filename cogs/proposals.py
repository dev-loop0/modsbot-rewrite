import asyncio

from discord.ext import commands

from cogs import config as cfg
from utils import potd_utils, split_utils

import re

from enum import IntEnum

Cog = commands.Cog


class Status(IntEnum):
    PENDING = 1
    ACCEPTED = 2
    REJECTED = 4
    UNKNOWN = 8


class Proposals(Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # schedule.every().hour.at("10:00").do(self.post_proposed_potd).tag(
        #     "cogs.proposals"
        # )

    def post_proposed_potd(self):
        self.bot.loop.create_task(self.post_proposed_potd_task())

    @commands.command(aliases=["idk"], brief="Checks proposals.")
    async def check_proposals(self, ctx):
        await self.post_proposed_potd_task()

    def get_proposals(self):
        return (
            cfg.Config.service.spreadsheets()
            .values()
            .get(spreadsheetId=cfg.Config.config["potd_proposal_sheet"], range="A:P")
            .execute()
            .get("values", [])
        )

    async def post_proposed_potd_task(self):
        # Read from spreadsheet
        proposed_problems = self.get_proposals()

        print(proposed_problems)

        for i, problem in enumerate(proposed_problems):
            # Find unposted problems
            if len(problem) < 14 or problem[13] == "":
                print("pass", i, "succeeded")
                number = i
                user = problem[1]
                user_id = problem[2]
                problem_statement = problem[3]
                source = problem[4]
                genre = problem[5]
                difficulty = problem[6]
                hint1 = problem[7]
                try:
                    hint2 = problem[8]
                except Exception:
                    hint2 = ""
                try:
                    hint3 = problem[9]
                except Exception:
                    hint3 = ""
                try:
                    proposer_msg = problem[10]
                except Exception:
                    proposer_msg = ""
                try:
                    solution = problem[11]
                except Exception:
                    solution = ""
                try:
                    solution_link = problem[12]
                except Exception:
                    solution_link = ""
                print("trying to post...")
                # Post in forum
                forum = self.bot.get_channel(cfg.Config.config["potd_proposal_forum"])
                content = (
                    f"POTD Proposal #{number} "
                    f"from {user} <@!{user_id}> ({user_id})\n"
                    f"Problem Statement: ```latex\n"
                    f"{problem_statement}\n```"
                )
                post_result = await forum.create_thread(
                    name=f"POTD Proposal #{number} from {user}",
                    content=content,
                    applied_tags=[
                        forum.get_tag(
                            cfg.Config.config["potd_proposal_forum_tag_pending"]
                        )
                    ],
                )
                thread = post_result[0]

                problem_info = (
                    f"Source: ||{source}|| \n"
                    + f"Genre: ||{genre}  || \n"
                    + f"Difficulty: ||{difficulty}  ||"
                )
                if proposer_msg not in ["", None]:
                    problem_info += f"\nProposer's message: {proposer_msg}\n"
                print("hi")
                await thread.send(problem_info)
                await asyncio.sleep(10)

                await thread.send("Hint 1:")
                await thread.send(
                    f"<@{cfg.Config.config['paradox_id']}> texsp\n"
                    f"||```latex\n{hint1}```||"
                )
                await asyncio.sleep(10)
                if hint2 not in ["", None]:
                    await thread.send("Hint 2:")
                    await thread.send(
                        f"<@{cfg.Config.config['paradox_id']}> texsp\n"
                        f"||```latex\n{hint2}```||"
                    )
                    await asyncio.sleep(10)
                if hint3 not in ["", None]:
                    await thread.send("Hint 3:")
                    await thread.send(
                        f"<@{cfg.Config.config['paradox_id']}> texsp\n"
                        f"||```latex\n{hint3}```||"
                    )
                    await asyncio.sleep(10)

                if solution not in ["", None]:
                    await thread.send("Solution:")
                    await thread.send(
                        f"<@{cfg.Config.config['paradox_id']}> texsp\n"
                        f"||```latex\n{solution}```||"
                    )
                    await asyncio.sleep(10)

                if solution_link not in ["", None]:
                    solution_link_msg = f"\nSolution link: {solution_link}\n"
                    await thread.send(solution_link_msg)
                    await asyncio.sleep(10)

                # Mark problem as posted
                # request = (
                #     cfg.Config.service.spreadsheets()
                #     .values()
                #     .update(
                #         spreadsheetId=cfg.Config.config["potd_proposal_sheet"],
                #         range=f"N{i+1}",
                #         valueInputOption="RAW",
                #         body={"range": f"N{i+1}", "values": [["Y"]]},
                #     )
                # )
                # request.execute()

                # Mark thread ID
                # request = (
                #     cfg.Config.service.spreadsheets()
                #     .values()
                #     .update(
                #         spreadsheetId=cfg.Config.config["potd_proposal_sheet"],
                #         range=f"O{i+1}",
                #         valueInputOption="RAW",
                #         body={"range": f"O{i+1}", "values": [[str(thread.id)]]},
                #     )
                # )
                # request.execute()

                # Initialize status as "Pending"
                # request = (
                #     cfg.Config.service.spreadsheets()
                #     .values()
                #     .update(
                #         spreadsheetId=cfg.Config.config["potd_proposal_sheet"],
                #         range=f"P{i+1}",
                #         valueInputOption="RAW",
                #         body={"range": f"P{i+1}", "values": [["Pending"]]},
                #     )
                # )
                # request.execute()

                # Send notification to proposer
                try:
                    guild = self.bot.get_guild(cfg.Config.config["mods_guild"])
                    member = guild.get_member(int(user_id))
                    if member is not None and not member.bot:
                        await member.send(
                            f"Hi! We have received your POTD Proposal `{source}`. "
                            "Thanks for your submission!"
                        )
                except Exception as e:
                    print(e)

    @commands.command()
    @commands.check(potd_utils.is_pc)
    async def potd_pending(self, ctx, number: int):
        await self.potd_proposal_status_change(ctx, number, "Pending")
        await ctx.send(f"POTD Proposal #{number} status modified to Pending")

    @commands.command()
    @commands.check(potd_utils.is_pc)
    async def potd_accept(self, ctx, number: int):
        await self.potd_proposal_status_change(ctx, number, "Accepted")
        await ctx.send(f"POTD Proposal #{number} status modified to Accepted")

    @commands.command()
    @commands.check(potd_utils.is_pc)
    async def potd_reject(self, ctx, number: int):
        await self.potd_proposal_status_change(ctx, number, "Rejected")
        await ctx.send(f"POTD Proposal #{number} status modified to Rejected")

    async def potd_proposal_status_change(self, ctx, number: int, status):
        tag_id = 0
        if status == "Pending":
            tag_id = cfg.Config.config["potd_proposal_forum_tag_pending"]
        elif status == "Accepted":
            tag_id = cfg.Config.config["potd_proposal_forum_tag_accepted"]
        elif status == "Rejected":
            tag_id = cfg.Config.config["potd_proposal_forum_tag_rejected"]

        # Load the proposal sheet
        proposed_problems = (
            cfg.Config.service.spreadsheets()
            .values()
            .get(spreadsheetId=cfg.Config.config["potd_proposal_sheet"], range="A:P")
            .execute()
            .get("values", [])
        )

        # Edit the thread tag
        forum = self.bot.get_channel(cfg.Config.config["potd_proposal_forum"])
        row = number
        thread_id = proposed_problems[row][14]
        thread = ctx.guild.get_thread(int(thread_id))
        await thread.edit(applied_tags=[forum.get_tag(tag_id)])

        # Edit the status in spreadsheet
        request = (
            cfg.Config.service.spreadsheets()
            .values()
            .update(
                spreadsheetId=cfg.Config.config["potd_proposal_sheet"],
                range=f"P{number+1}",
                valueInputOption="RAW",
                body={"range": f"P{number+1}", "values": [[status]]},
            )
        )
        request.execute()

    def get_status(self, proposal: list):
        if len(proposal) < 14 or proposal[13] == "":
            return Status.PENDING
        else:
            if proposal[15] == "Pending":
                return Status.PENDING
            elif proposal[15] == "Accepted":
                return Status.ACCEPTED
            elif proposal[15] == "Rejected":
                return Status.REJECTED
            else:
                return Status.UNKNOWN

    # manually invoke the proposal check
    @commands.command()
    @commands.check(cfg.is_mod_or_tech)
    async def potd_proposal(self, ctx):
        self.bot.loop.create_task(self.post_proposed_potd_task())

    @commands.command(aliases=["myproposals"], brief="Checks your proposals.")
    async def potd_myproposals(self, ctx, *args):
        short_flags = ""
        long_flags = []
        user_id = None
        for argument in args:
            if argument.startswith("--"):
                long_flags.append(argument[2:])
            elif argument.startswith("-"):
                short_flags += argument[1:]
            elif user_id is None:
                user_id = argument

        if user_id is None:
            user_id = str(ctx.author.id)
        else:
            if user_id.startswith("<@") and user_id.endswith(">"):
                user_id = user_id[2:-1]
            try:
                _ = int(user_id)
            except ValueError:
                await ctx.send("Argument is not a user id!")
                return

        sort_by_number = "n" in short_flags or "number" in long_flags
        sort_by_source = "s" in short_flags or "source" in long_flags
        filter_pending = "p" in short_flags or "pending" in long_flags
        filter_accepted = "a" in short_flags or "accepted" in long_flags
        filter_rejected = "r" in short_flags or "rejected" in long_flags
        sort_ascending = "A" in short_flags or "ascending" in long_flags
        sort_descending = "D" in short_flags or "descending" in long_flags

        if sort_by_number + sort_by_source == 0:
            sort_by_number = True
        elif sort_by_number + sort_by_source >= 2:
            await ctx.send("Cannot sort by more than one field!")
            return

        proposals = enumerate(self.get_proposals())

        mask = 0
        if filter_pending + filter_accepted + filter_rejected == 0:
            mask = Status.PENDING | Status.ACCEPTED | Status.REJECTED
        if filter_pending:
            mask |= Status.PENDING
        if filter_accepted:
            mask |= Status.ACCEPTED
        if filter_rejected:
            mask |= Status.REJECTED

        if filter_pending + filter_accepted + filter_rejected == 0:
            user_proposals = filter(lambda x: x[1][2] == user_id, proposals)
        else:
            user_proposals = filter(
                lambda x: x[1][2] == user_id and self.get_status(x[1]) & mask, proposals
            )

        if sort_ascending + sort_descending == 0:
            sort_ascending = True
        elif sort_ascending + sort_descending >= 2:
            await ctx.send(
                "Cannot sort both in ascending order and in descending order!"
            )
            return

        # construct output
        lines = []
        for proposal in user_proposals:
            line = []

            line.append(f"{proposal[0]:3}")

            # parse timestamp
            match = re.search(r"^(\d+)/(\d+)/(\d+) (\d+):(\d+):(\d+)$", proposal[1][0])
            if match:
                line.append(
                    f"{match.group(3)}-{match.group(1):0>2}-{match.group(2):0>2}"
                )
            else:
                line.append("????-??-??")

            width = cfg.Config.config["proposal_source_width"]
            line.append(f"{proposal[1][4]:<{width}.{width}}")

            line.append(
                {
                    Status.PENDING: "\x1b[2;33mPending\x1b[0m",
                    Status.ACCEPTED: "\x1b[2;32mAccepted\x1b[0m",
                    Status.REJECTED: "\x1b[2;31mRejected\x1b[0m",
                    Status.UNKNOWN: "Unknown",
                }[self.get_status(proposal[1])]
            )

            lines.append(line)

        if not lines:
            await ctx.send("No results match your query.")
        else:
            # should already be sorted by number
            if sort_by_source:
                lines.sort(key=lambda x: x[2])
            if sort_descending:
                lines.reverse()
            batches = split_utils.split_with_limit(
                "\n".join([" · ".join(i) for i in lines]), "\n", 1900
            )
            for i in range(len(batches)):
                batches[i] = "```ansi\n" + batches[i] + "```"
            batches[0] = "# __Your proposals__\n" + batches[0]
            for batch in batches:
                await ctx.send(batch)


async def setup(bot):
    await bot.add_cog(Proposals(bot))
