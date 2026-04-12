import asyncio
from datetime import datetime
from enum import IntFlag

from discord.ext import commands

from cogs import config as cfg
from utils import potd_utils

Cog = commands.Cog


class Status(IntFlag):
    PENDING = 0x01
    ACCEPTED = 0x02
    REJECTED = 0x04
    UNKNOWN = 0x08


class SortType(IntFlag):
    NUMBER = 0x00
    SOURCE = 0x01
    ASCENDING = 0x00
    DESCENDING = 0x10


from cogs.menus import PageType  # noqa: E402


class Proposal:
    def __init__(self, problem: list, number: int):
        problem += [""] * min(0, 13 - len(problem))

        self.number = number

        try:
            self.timestamp = datetime.strptime(problem[0], "%m/%d/%Y %H:%M:%S")
        except ValueError:
            self.timestamp = None

        (
            self.user,
            self.user_id,
            self.problem_statement,
            self.source,
            self.genre,
            self.difficulty,
            self.hint1,
            self.hint2,
            self.hint3,
            self.proposer_msg,
            self.solution,
            self.solution_link,
        ) = problem[1:13]

        if len(problem) < 14 or problem[13] == "":
            self.status = Status.PENDING
        else:
            if problem[15] == "Pending":
                self.status = Status.PENDING
            elif problem[15] == "Accepted":
                self.status = Status.ACCEPTED
            elif problem[15] == "Rejected":
                self.status = Status.REJECTED
            else:
                self.status = Status.UNKNOWN

    def prettify(self) -> list:
        output = []

        output.append(f"{self.number:3}")

        if self.timestamp is not None:
            output.append(self.timestamp.strftime("%Y-%m-%d"))
        else:
            output.append("????-??-??")

        width = cfg.Config.config["proposal_source_width"]
        output.append(f"{self.source:<{width}.{width}}")

        output.append(
            {
                Status.PENDING: "\x1b[2;33mPending\x1b[0m",
                Status.ACCEPTED: "\x1b[2;32mAccepted\x1b[0m",
                Status.REJECTED: "\x1b[2;31mRejected\x1b[0m",
                Status.UNKNOWN: "Unknown",
            }[self.status]
        )

        return output


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

        for i, problem in enumerate(proposed_problems):
            # Find unposted problems
            if len(problem) < 14 or problem[13] == "":
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
        if args:
            user_id = args[0]
            if user_id.startswith("<@") and user_id.endswith(">"):
                user_id = user_id[2:-1]
            try:
                _ = int(user_id)
            except ValueError:
                await ctx.send("Argument is not a user id!")
                return
        else:
            user_id = str(ctx.author.id)

        proposals = []
        for i, proposal in enumerate(self.get_proposals()):
            proposals.append(Proposal(proposal, i))

        user_proposals = list(filter(lambda x: x.user_id == user_id, proposals))

        if not user_proposals:
            await ctx.send("No results match your query.")
        else:
            await self.bot.get_cog("MenuManager").new_filter_sort_menu(
                ctx, user_proposals, page_type=PageType.TEXT
            )


async def setup(bot):
    await bot.add_cog(Proposals(bot))
