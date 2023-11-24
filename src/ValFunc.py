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
    teammatesLeft: int
    enemiesLeft: int

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

@dataclass
class RoundStats:
    startTime: int # in terms of matchTime (ms)
    length: int # in terms of milliseconds
    endType: str # how round ended (Eliminated, Bomb defused, Bomb detonated, Round timer expired)
    kills: list[Kill] # kill times in milliseconds
    scoreUptoRound: str # score before this round (current player first)
    numKills: int # kills by current player
    isClutch: bool # if player clutched
    isKills: bool # if any kills were made


class MatchStats:
    def __init__(self, match_id, player_puuid):
        data = getJSON(f'https://api.henrikdev.xyz/valorant/v2/match/{match_id}')["data"]
        player = None
        for player_data in data["players"]["all_players"]:
            if player_data["puuid"] == player_puuid:
                player = player_data
                break
        if player is None:
            raise ValueError(f"Selected player not found in given match ID")
        self.playerTeam = player["team"]
        teamToLower = self.playerTeam.lower()
        self.map = data["metadata"]["map"]
        self.rounds = []
        self.chapterTimes = []
        self.playerStats = PlayerStats(
            data["teams"][teamToLower]["has_won"],
            round(player["stats"]["score"] / data["metadata"]["rounds_played"]),
            player["stats"]["kills"],
            player["stats"]["deaths"],
            player["stats"]["assists"],
            player["currenttier_patched"],
            player["currenttier"],
            player["character"]
        )
        # Get round stats
        playerTeamScore = 0
        enemyTeamScore = 0
        for i in range(data["metadata"]["rounds_played"]):
            round_kills = []
            curRound = data["rounds"][i]
            # Get kill stats
            playerClutchPos = False # player starts in non clutch position
            for kill in data["kills"]:
                if kill["round"] == i:
                    # find how many people are left at kill time
                    teamLeft = 0
                    enemLeft = 0
                    isPlayerAlive = False
                    for playerLocation in kill["player_locations_on_kill"]:
                        if playerLocation["player_team"] == self.playerTeam:
                            teamLeft += 1
                            if playerLocation["player_puuid"] == player["puuid"]:
                                isPlayerAlive = True
                        else:
                            enemLeft += 1
                    if isPlayerAlive and teamLeft == 1 and enemLeft > 1 and not playerClutchPos:
                        playerClutchPos = True
                        playerClutchPosTime = kill["kill_time_in_round"]
                    # Push kill stats
                    round_kills.append(Kill(
                        kill["kill_time_in_round"],
                        kill["kill_time_in_match"],
                        teamLeft,
                        enemLeft
                    ))
            round_isKills = round_kills
            # Get end type
            round_endType = curRound["end_type"]
            # Get round lenght
            if round_endType == "Eliminated":
                round_length = round_kills[-1].timeInRound
            elif round_endType == "Bomb defused":
                round_length = curRound["defuse_events"]["defuse_time_in_round"]
            elif round_endType == "Bomb detonated":
                round_length = curRound["plant_events"]["plant_time_in_round"] + 45_000 # 45 seconds after plant time
            else:
                round_length = 100_000 # round timer expired (100 seconds, 1:40 minutes)
            # Get round start time
            if round_isKills:
                round_startTime = round_kills[0].timeInMatch - round_kills[0].timeInRound
            elif i == 0:
                round_startTime = 56_000 # guess first round starts at about 56 seconds
            elif i == 12:
                round_startTime = self.rounds[i-1].startTime + self.rounds[i-1].length + 52_000 # post-round (7 sec) + halftime (45 sec)
            else:
                round_startTime = self.rounds[i-1].startTime + self.rounds[i-1].length + 37_000 # post-round (7 sec) + pre-round (30 sec)
            # Get player kills
            for playerStat in curRound["player_stats"]:
                if playerStat["player_puuid"] == player_puuid:
                    round_numKills = playerStat["kills"]
                    for killEvent in playerStat["kill_events"]:
                        if killEvent["killer_team"] == killEvent["victim_team"]:
                            round_numKills -= 1 # subtract team kills
                    break
            # Get score before round
            round_scoreUptoRound = f'{playerTeamScore}-{enemyTeamScore}'
            if curRound["winning_team"] == self.playerTeam:
                playerTeamScore += 1
                wonRound = True
            else:
                enemyTeamScore += 1
                wonRound = False
            if playerClutchPos and wonRound and playerClutchPosTime < round_length:
                round_isClutch = True
            else:
                round_isClutch = False
            # push round stats
            self.rounds.append(RoundStats(
                round_startTime,
                round_length,
                round_endType,
                round_kills,
                round_scoreUptoRound,
                round_numKills,
                round_isClutch,
                round_isKills
            ))
            # get and push chapter time
            if i == 0:
                self.chapterTimes.append(round(round_startTime / 1_000) - 45)
            else:
                self.chapterTimes.append(round(round_startTime / 1_000) - 30)

    def get_chapters(self, startTimeSec=60):
        output = f'{self.playerStats.agent} {self.map} {self.playerStats.curRank}\n'
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
            output += f':{sec:02d} Round {i+1} | {curRound.scoreUptoRound} | {curRound.numKills}k'
            if curRound.isClutch:
                output += ' | CLUTCH'
            output += '\n'
        return output


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
    