import json # parce received API data
import requests # for API GET
from dataclasses import dataclass 


def str_to_user_gt(string):
    strlist = string.rstrip().split('#')
    if len(strlist) != 2:
        raise ValueError(f'Error: {string} is not a valid username and tagline')
    if len(strlist[0]) < 3 or len(strlist[0]) > 16:
        raise ValueError(f'Error: {strlist[0]} is not a valid username')
    if len(strlist[1]) < 3 or len(strlist[1]) > 5:
        raise ValueError(f'Error: {strlist[1]} is not a valid tagline')
    return strlist[0], strlist[1]
    
def getJSON(url):
    try:
        jsonOut = None
        r = requests.get(url, timeout=5)
        jsonOut = json.loads(r.text)
        r.raise_for_status()
    except requests.exceptions.HTTPError as he:
        if jsonOut is not None:
            raise APIError(jsonOut) from he
        else:
            raise RequestError(f'HTTP Error: {he}') from he
    except requests.exceptions.ConnectionError as ce:
        raise RequestError('Connection Error') from ce
    except requests.exceptions.Timeout as te:
        raise RequestError('Timeout') from te
    except requests.exceptions.RequestException as re:
        raise RequestError('Error') from re
    except ValueError as ve:
        raise RequestError('Response not valid JSON') from ve
    return jsonOut

def gt_to_puuid(username, tagline):
    return getJSON(f'https://api.henrikdev.xyz/valorant/v1/account/{username}/{tagline}')["data"]["puuid"]

def puuid_to_gt(puuid):
    js = getJSON(f'https://api.henrikdev.xyz/valorant/v1/by-puuid/account/{puuid}')
    return [js["data"]["name"], js["data"]["tag"]]

def get_region(puuid_or_username, tagline=None):
    if tagline is None:
        return getJSON(f'https://api.henrikdev.xyz/valorant/v1/by-puuid/account/{puuid_or_username}')["data"]["region"]
    else:
        return getJSON(f'https://api.henrikdev.xyz/valorant/v1/account/{puuid_or_username}/{tagline}')["data"]["region"]

def list_last_matches(puuid_or_username, tagline=None, region=None):
    if tagline is None:
        if region is None:
            region = get_region(puuid_or_username)
        url = f'https://api.henrikdev.xyz/valorant/v1/by-puuid/mmr-history/{region}/{puuid_or_username}'
    else:
        if region is None:
            region = get_region(puuid_or_username, tagline)
        url = f'https://api.henrikdev.xyz/valorant/v1/mmr-history/{region}/{puuid_or_username}/{tagline}'
    return [i["match_id"] for i in getJSON(url)["data"]]


@dataclass
class Kill:
    timeInRound: int
    timeInMatch: int
    killer_puuid: str
    killer_team: str
    victim_puuid: str
    victim_team: str
    teammatesLeft: int
    enemiesLeft: int
    playersLeft: list[str] # player puuids

@dataclass
class RoundStats:
    win: bool # if player/team won or not
    startTime: int # in terms of matchTime (ms)
    length: int # in terms of milliseconds
    endType: str # how round ended (Eliminated, Bomb defused, Bomb detonated, Round timer expired)
    kills: list[Kill] # kill times in milliseconds
    scoreUptoRound: str # score before this round (current player first)
    isKills: bool # if any kills were made

@dataclass
class PlayerRoundStats:
    numKills: int # kills by current player
    isClutch: bool # if player clutched

@dataclass
class PlayerStats:
    win: bool # if player won or not
    acs: int
    kills: int
    deaths: int
    assists: int
    curRank: str
    competitiveTier: int
    agent: str
    rounds: list[PlayerRoundStats]



class MatchStats:
    def __init__(self, data, curTeam):
        self.map: str = data["metadata"]["map"]
        self.rounds: list[RoundStats] = []
        self.chapterTimes: list[int] = []
        curTeamScore = 0
        oppTeamScore = 0
        for i in range(data["metadata"]["rounds_played"]):
            round_kills: list[Kill] = []
            curRound = data["rounds"][i]
            # GET round kills
            for kill in data["kills"]:
                if kill["round"] == i:
                    teamLeft = 0
                    enemLeft = 0
                    playerList = []
                    for playerLocation in kill["player_locations_on_kill"]:
                        if playerLocation["player_team"] == curTeam:
                            teamLeft += 1
                        else:
                            enemLeft += 1
                        playerList.append(playerLocation["player_puuid"])
                    round_kills.append(Kill(
                        kill["kill_time_in_round"],
                        kill["kill_time_in_match"],
                        kill["killer_puuid"],
                        kill["killer_team"],
                        kill["victim_puuid"],
                        kill["victim_team"],
                        teamLeft,
                        enemLeft,
                        playerList
                    ))
            round_isKills = len(round_kills) > 0
            # GET end type
            round_endType = curRound["end_type"]
            # GET round length
            if round_endType == 'Eliminated':
                round_length = round_kills[-1].timeInRound
            elif round_endType == 'Bomb defused':
                round_length = curRound["defuse_events"]["defuse_time_in_round"]
            elif round_endType == 'Bomb detonated':
                round_length = curRound["plant_events"]["plant_time_in_round"] + 45_000 # 45 seconds after plant time
            else:
                round_length = 100_000 # round timer expired (100 seconds, 1:40 minutes)
            # GET round start time
            if round_isKills:
                round_startTime = round_kills[0].timeInMatch - round_kills[0].timeInRound
            elif i == 0:
                round_startTime = 56_000 # guess first round starts at about 56 seconds
            elif i == 12:
                round_startTime = self.rounds[i-1].startTime + self.rounds[i-1].length + 52_000 # post-round (7 sec) + halftime (45 sec)
            else:
                round_startTime = self.rounds[i-1].startTime + self.rounds[i-1].length + 37_000 # post-round (7 sec) + pre-round (30 sec)
            # GET score before round
            round_scoreUptoRound = f'{curTeamScore} - {oppTeamScore}'
            if curRound["winning_team"] == curTeam:
                curTeamScore += 1
                round_won = True
            else:
                oppTeamScore += 1
                round_won = False
            # PUSH round stats
            self.rounds.append(RoundStats(
                round_won,
                round_startTime,
                round_length,
                round_endType,
                round_kills,
                round_scoreUptoRound,
                round_isKills
            ))
            # GET and PUSH chapter time
            if i == 0:
                self.chapterTimes.append(round(round_startTime / 1_000) - 45)
            else:
                self.chapterTimes.append(round(round_startTime / 1_000) - 30)
    
    def get_chapters(self, startTimeSec=60, title=None, postfixList=None):
        output = ''
        if title is not None:
            output += f'{title}\n'
        for i in range(len(self.rounds)):
            curRound = self.rounds[i]
            sec = startTimeSec - 45 + self.chapterTimes[i] - self.chapterTimes[0]
            if i == 12:
                sec -= 15
            if sec < 0:
                sec = -sec
                isNegative = True
            else:
                isNegative = False
            hr = sec // 3600
            min = (sec // 60) % 60
            sec %= 60
            if isNegative:
                output += '-'
            if hr == 0:
                output += f'{min}'
            else:
                output += f'{hr}:{min:02d}'
            output += f':{sec:02d} Round {i+1} | {curRound.scoreUptoRound}'
            if postfixList is not None:
                output += f' | {postfixList[i]}'
            output += '\n'
        return output


class PlayerMatchStats(MatchStats):
    def __init__(self, match_id, player_puuid):
        data = getJSON(f'https://api.henrikdev.xyz/valorant/v2/match/{match_id}')["data"]
        player = None
        for player_data in data["players"]["all_players"]:
            if player_data["puuid"] == player_puuid:
                player = player_data
                break
        if player is None:
            raise ValueError(f"Selected player not found in given match ID")
        self.team: str = player["team"]
        super().__init__(data, self.team)
        playerRoundsStats: list[PlayerRoundStats] = []
        for curRound in self.rounds:
            playerKills = 0
            playerClutchPos = False
            for kill in curRound.kills:
                if kill.killer_puuid == player_puuid and kill.victim_team != self.team:
                    playerKills += 1
                isPlayerAlive = False
                for puuid in kill.playersLeft:
                    if puuid == player_puuid:
                        isPlayerAlive = True
                        break
                if isPlayerAlive and kill.teammatesLeft == 1 and kill.enemiesLeft > 1 and not playerClutchPos:
                    playerClutchPos = True
                    playerClutchPosTime = kill.timeInRound
            if playerClutchPos and curRound.win and playerClutchPosTime < curRound.length:
                isClutch = True 
            else:
                isClutch = False
            playerRoundsStats.append(PlayerRoundStats(
                playerKills,
                isClutch
            ))
        self.playerStats = PlayerStats(
            data["teams"][self.team.lower()]["has_won"],
            round(player["stats"]["score"] / data["metadata"]["rounds_played"]),
            player["stats"]["kills"],
            player["stats"]["deaths"],
            player["stats"]["assists"],
            player["currenttier_patched"],
            player["currenttier"],
            player["character"],
            playerRoundsStats
        )
    
    def get_chapters(self, startTimeSec=60):
        title = f'{self.playerStats.agent} {self.map} {self.playerStats.curRank}'
        lineList: list[str] = []
        for round in self.playerStats.rounds:
            line = f'{round.numKills}k'
            if round.isClutch:
                line += ' | CLUTCH'
            lineList.append(line)
        return super().get_chapters(startTimeSec, title, lineList)


class APIError(Exception):
    def __init__(self, json):
        self.json = json
        self.status = json.get('status', 'Unknown Status')
        self.message = 'API error occurred'
        if self.status != 'Unknown Status':
            self.message = f'API Error: {self.status} - {json.get("errors", [{}])[0].get("message", "Unknown error")}'
        super().__init__(self.message)

class RequestError(Exception):
    pass



if __name__ == '__main__':
    # matchEx = 'https://api.henrikdev.xyz/valorant/v2/match/c53ed888-774e-4df7-97d0-948186911506' # 10/24/23 comp on lotus
    # nameEx = 'https://api.henrikdev.xyz/valorant/v1/account/UNH%20treYmur/TTMMC'
    
    # stats = MatchStats('80fbed4c-1f3b-4fbf-b344-5007c9287de0', gt_to_puuid('Woohoojin', 'COACH'))
    # print(stats.get_chapters(60))
    
    user, tag = str_to_user_gt('UNH treYmur#COACH ')
    print(f"Username:{user}, Tagline:{tag}")
    