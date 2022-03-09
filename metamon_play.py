import argparse
from tqdm import trange
import requests
import os
import sys
import csv
import pandas as pd
from time import sleep
from datetime import datetime
from operator import itemgetter
import json
import sys

# URLs to make api calls
BASE_URL = "https://metamon-api.radiocaca.com/usm-api"
TOKEN_URL = f"{BASE_URL}/login"
LIST_MONSTER_URL = f"{BASE_URL}/getWalletPropertyBySymbol"
CHANGE_FIGHTER_URL = f"{BASE_URL}/isFightMonster"
START_FIGHT_URL = f"{BASE_URL}/startBattle"
LIST_BATTLER_URL = f"{BASE_URL}/getBattelObjects"
WALLET_PROPERTY_LIST = f"{BASE_URL}/getWalletPropertyList"
LVL_UP_URL = f"{BASE_URL}/updateMonster"
MINT_EGG_URL = f"{BASE_URL}/composeMonsterEgg"
CHECK_BAG_URL = f"{BASE_URL}/checkBag"
EXP_UP_URL = f"{BASE_URL}/expUpMonster"
POWER_UP_URL = f"{BASE_URL}/addAttr"
DEFAULT_METAMON_BATTLE = '{"code":"SUCCESS","data":{"objects":[{"con":97,"conMax":200,"crg":48,"crgMax":100,"id":"714892","inte":96,"inteMax":200,"inv":48,"luk":19,"lukMax":50, "level":"16","race":"demon","rarity":"N","sca":308,"tokenId":""}]}}'
def datetime_now():
    return datetime.now().strftime("%m/%d/%Y %H:%M:%S")


def post_formdata(payload, url="", headers=None, params=None):
    """Method to send request to game"""
    files = []
    if headers is None:
        headers = {}
    if params is None:
        params = {}
    for _ in range(5):
        try:
            # Add delay to avoid error from too many requests per second
            sleep(1)
            response = requests.request("POST",
                                        url,
                                        headers=headers,
                                        data=payload,
                                        params=params,
                                        files=files)
            return response.json()
        except:
            continue
    return {}


def get_battler_score(monster):
    """ Get opponent's power score"""
    return monster["sca"]


def picker_battler(monsters_list, other_fighting_mode):
    """ Picking opponent """
    battlers = list(filter(lambda m: m["rarity"] == "N", monsters_list))

    if len(battlers) == 0:
        battlers = list(filter(lambda m: m["rarity"] == "R", monsters_list))

    battler = battlers[0]
    score_min = get_battler_score(battler)
   
    for i in range(1, len(battlers)):
        score = get_battler_score(battlers[i])
        if score < score_min:
            battler = battlers[i]
            score_min = score
    if other_fighting_mode[0] == True:
        battlers_sorted = sorted(battlers, key=itemgetter('sca','luk', 'crg', 'inv', 'con', 'inte'))
        battler = battlers[0]
        
    my_monster_id = battler.get("id")
    my_luk = battler.get("luk")
    my_size = battler.get("con")
    my_inte = battler.get("inte")
    my_courage = battler.get("crg")
    my_inv = battler.get("inv")
    my_level = battler.get("level")
    my_power = battler.get("sca")
    my_race = battler.get("race")
    print(f"Battle Monsters - ID: {my_monster_id}, Race:{my_race}, Score: {my_power}, Luk: {my_luk}, Wisdom: {my_inte}, Size: {my_size}, Courage: {my_courage}, Stealth: {my_inv}")
    return battler


def pick_battle_level(level=1):
    # pick highest league for given level
    if 21 <= level <= 40:
        return 2
    if 41 <= level <= 60:
        return 3
    return 1


class MetamonPlayer:

    def __init__(self,
                 address,
                 sign,
                 msg="LogIn",
                 auto_lvl_up=False,
                 other_fighting_mode = False,
                 lowest_score = False,
                 auto_exp_up = False,
                 auto_power_up = False,
                 battle_record = False,
                 output_stats=False):
        self.no_enough_money = False
        self.output_stats = output_stats
        self.total_bp_num = 0
        self.total_success = 0
        self.total_fail = 0
        self.total_powup_success = 0
        self.total_powup_fail = 0
        self.mtm_stats_df = []
        self.token = None
        self.address = address
        self.sign = sign
        self.msg = msg
        self.auto_lvl_up = auto_lvl_up,
        self.other_fighting_mode = other_fighting_mode,
        self.lowest_score = lowest_score
        self.auto_exp_up = auto_exp_up,
        self.auto_power_up = auto_power_up,
        self.battle_record = battle_record,
        self.rate = 0

    def init_token(self):
        """Obtain token for game session to perform battles and other actions"""
        payload = {"address": self.address, "sign": self.sign, "msg": self.msg, "network": "1", "clientType": "MetaMask"}
        response = post_formdata(payload, TOKEN_URL)
        if response.get("code") != "SUCCESS":
            sys.stderr.write("Login failed, token is not initialized. Terminating\n")
            sys.exit(-1)
        self.token = response.get("data").get("accessToken")

    def change_fighter(self, monster_id):
        """Switch to next metamon if you have few"""
        payload = {
            "metamonId": monster_id,
            "address": self.address,
        }
        post_formdata(payload, CHANGE_FIGHTER_URL)

    def list_battlers(self, monster_id, front=1):
        """Obtain list of opponents"""
        if self.lowest_score == True:
            response = json.loads(DEFAULT_METAMON_BATTLE)
            return response.get("data", {}).get("objects")
        else:
            payload = {
            "address": self.address,
            "metamonId": monster_id,
            "front": front,
            }
            headers = {
            "accessToken": self.token,
            }
            response = post_formdata(payload, LIST_BATTLER_URL, headers)
            return response.get("data", {}).get("objects")
        
        
    def exp_up(self, monster_id):
        """Up exp for metamon"""
        payload = {
            "address": self.address,
            "nftId": monster_id
        }
        headers = {
            "accessToken": self.token,
        }
        response = post_formdata(payload, EXP_UP_URL, headers)
        return response
        
    def power_up(self, monster_id, attr_type = 1):
        """Up exp for metamon"""
        payload = {
            "attrType": attr_type,
            "nftId": monster_id
        }
        params = {'address': self.address}
        headers = {
            "accessToken": self.token,
        }
        response = post_formdata(payload, POWER_UP_URL, headers, params)
        return response    
        
    def auto_up_exp(self):
        """Automatically up exp for metamon"""
        self.init_token()
        wallet_monsters = self.get_wallet_properties()
        for monster in wallet_monsters:
            my_monster_token_id = monster.get("tokenId")
            my_monster_id = monster.get("id")
            exp_up_response = self.exp_up(my_monster_id) 
            while (exp_up_response.get("code") == "SUCCESS"):
                data = exp_up_response.get("data")
                print(f"+{data} EXP FOR METAMON {my_monster_token_id}")
                exp_up_response = self.exp_up(my_monster_id)
        print("Automatically exp up finish")
            
    def auto_up_power(self):
        """Automatically up power for metamon"""
        #TODO
        self.init_token()
        wallet_monsters = self.get_wallet_properties()
        available_monsters = [
            monster for monster in wallet_monsters if monster.get("allowUpper") == True
        ]
        print(f"Available Metamon to up power: {len(available_monsters)}")
        for monster in available_monsters:
            my_monster_token_id = monster.get("tokenId")
            my_monster_id = monster.get("id")
            my_luk = monster.get("luk")
            my_size = monster.get("con")
            my_inte = monster.get("inte")
            my_courage = monster.get("crg")
            my_inv = monster.get("inv")
            attr_up_type = 1
            attr_up_name = "Luck"
            if my_courage < 50:
                attr_up_type = 2
                attr_up_name = "Courage"
            elif my_inte < 101:
                attr_up_type = 3
                attr_up_name = "Wisdom"
            elif my_size < 101:
                attr_up_type = 4
                attr_up_name = "Size"
            elif my_inv < 50:
                attr_up_type = 5
                attr_up_name = "Stealth"
            power_up_response = self.power_up(my_monster_id, attr_up_type)
            if power_up_response.get("code") == "SUCCESS":
                data = power_up_response.get("data")
                if data.get("upperNum") == 0:
                    print(f"\nUp {attr_up_name} for metamon {my_monster_token_id} failed")
                else:
                    attr_num = data.get("attrNum")
                    upper_num = data.get("upperNum")
                    upper_attr_num = data.get("upperAttrNum")
                    sca = data.get("sca")
                    upper_sca = data.get("upperSca")
                    print(f"{attr_up_name} of metamon {my_monster_token_id} +{upper_num}: {attr_num} -> {upper_attr_num}")
                    print(f"Score of metamon {my_monster_token_id}: {sca} -> {upper_sca}")
            else:
                print(f"Up {attr_up_name} for metamon {my_monster_token_id} unsuccesful")
         
    def display_battle(self,
                       challenge_record,
                       challenge_monster,
                       my_monster_id,
                       my_monster_size,
                       my_monster_inv,
                       my_monster_crg,
                       my_monster_inte):
        count = 0
        opponent_crit_count = 0;
        for record in challenge_record:

            count += 1
            target_monster_size = challenge_monster.get("con")
            target_monster_inte = challenge_monster.get("inte")
            target_monster_crg = challenge_monster.get("crg")
            target_monster_inv = challenge_monster.get("inv")
            
            monsteraId = record.get("monsteraId")
            attackType = record.get("attackType")
            defenceType = record.get("defenceType")
            monsteraLife = record.get("monsteraLife")
            #monsterBLife = record.get("monsterbLife")
            attackTypeStr = ""
            defenceTypeStr = ""
            
            finalDame = record.get("monsterbLifelost")
            old_stdout = sys.stdout
            log_file = open("battle_record.log","w")
            sys.stdout = log_file
            
            if attackType == 0:
               attackTypeStr = "Wisdom"
            else:
               attackTypeStr = "Size"
            if defenceTypeStr == 0:
               defenceTypeStr = "Courage"
            else:
               defenceTypeStr = "Stealth"               
            print(f"\n Turn {count} - Attack Attribute: {attackTypeStr}, Defence Attribute: {defenceTypeStr}")
            if monsteraId == my_monster_id:
                print(f"\n- My Metamon Fighting:    Health: {monsteraLife}, Final Dame = {finalDame}")
                if attackType == 0 and defenceType == 0:
                    if finalDame == (my_monster_inte - target_monster_crg*2) or finalDame == (my_monster_inte*2 - target_monster_crg*2):
                        opponent_crit_count += 1
                elif attackType == 0 and defenceType == 1:
                    if finalDame == (my_monster_inte - target_monster_inv*2) or finalDame == (my_monster_inte*2 - target_monster_inv*2):
                        opponent_crit_count += 1                
                elif attackType == 1 and defenceType == 0:
                    if finalDame == (my_monster_size - target_monster_crg*2) or finalDame == (my_monster_size*2 - target_monster_crg*2):
                        opponent_crit_count += 1                  
                elif attackType == 1 and defenceType == 1:
                    if finalDame == (my_monster_size - target_monster_inv*2) or finalDame == (my_monster_size*2 - target_monster_inv*2):
                        opponent_crit_count += 1                   
            else:
                print(f"\n- Opponent's Metamon Fighting:   Health: {monsteraLife}, Final Dame = {finalDame}")
                if attackType == 0 and defenceType == 0:
                    if finalDame == (target_monster_inte*2 - my_monster_crg) or finalDame == (target_monster_inte*2 - my_monster_crg*2):
                        opponent_crit_count += 1
                elif attackType == 0 and defenceType == 1:
                    if finalDame == (target_monster_inte*2 - my_monster_inv) or finalDame == (target_monster_inte*2 - my_monster_inv*2):
                        opponent_crit_count += 1                
                elif attackType == 1 and defenceType == 0:
                    if finalDame == (target_monster_size*2 - my_monster_crg) or finalDame == (target_monster_size*2 - my_monster_crg*2):
                        opponent_crit_count += 1                  
                elif attackType == 1 and defenceType == 1:
                    if finalDame == (target_monster_size*2 - my_monster_inv) or finalDame == (target_monster_size*2 - my_monster_inv*2):
                        opponent_crit_count += 1
        print(f"\nOpponent's crit: {opponent_crit_count} times in battle")
        
        sys.stdout = old_stdout
        log_file.close()
        return opponent_crit_count
             
    def start_fight(self,
                    my_monster,
                    target_monster_id,
                    target_monster_race,
                    target_monster_size,
                    target_monster_luk,
                    target_monster_inv,
                    target_monster_crg,
                    target_monster_inte,
                    target_monster_sca,
                    loop_count=1):
        """ Main method to initiate battles (as many as monster has energy for)"""
        success = 0
        fail = 0
        total_bp_fragment_num = 0
        mtm_stats = []
        my_monster_id = my_monster.get("id")
        my_monster_token_id = my_monster.get("tokenId")
        my_luk = my_monster.get("luk")
        my_size = my_monster.get("con")
        my_inte = my_monster.get("inte")
        my_courage = my_monster.get("crg")
        my_inv = my_monster.get("inv")
        my_level = my_monster.get("level")
        my_power = my_monster.get("sca")
        my_race = my_monster.get("race")
        my_allow_upper = my_monster.get("allowUpper")
        battle_level = pick_battle_level(my_level)
        tbar = trange(loop_count)
        
        if  self.auto_exp_up[0] == True:    
            exp_up_response = self.exp_up(my_monster_id)
            while (exp_up_response.get("code") == "SUCCESS"):
                data = exp_up_response.get("data")
                print(f"\nEXP UP FOR METAMON {my_monster_token_id} SUCCESS : +{data}")
                exp_up_response = self.exp_up(my_monster_id)
            if self.auto_lvl_up:
                # Try to lvl up
                headers = {
                    "accessToken": self.token,
                }
                res = post_formdata({"nftId": my_monster_id, "address": self.address},
                                    LVL_UP_URL,
                                    headers)
                code = res.get("code")
                if code == "SUCCESS":
                    tbar.set_description("LVL UP successful! Continue fighting...")
                    my_level += 1
                    # Update league level if new level is 21 or 41
                    battle_level = pick_battle_level(my_level)
        if self.auto_power_up[0] == True and my_allow_upper == True:
            attr_up_type = 1
            attr_up_name = "Luck"
            if my_courage < 50:
                attr_up_type = 2
                attr_up_name = "Courage"
            elif my_inte < 101:
                attr_up_type = 3
                attr_up_name = "Wisdom"
            elif my_size < 101:
                attr_up_type = 4
                attr_up_name = "Size"
            elif my_inv < 50:
                attr_up_type = 5
                attr_up_name = "Stealth"
            power_up_response = self.power_up(my_monster_id, attr_up_type)
            if power_up_response.get("code") == "SUCCESS":
                data = power_up_response.get("data")
                if data.get("upperNum") == 0:
                    self.total_powup_fail += 1
                    print(f"\nUp {attr_up_name} for metamon {my_monster_token_id} failed")
                else:
                    attr_num = data.get("attrNum")
                    upper_num = data.get("upperNum")
                    upper_attr_num = data.get("upperAttrNum")
                    sca = data.get("sca")
                    upper_sca = data.get("upperSca")
                    self.total_powup_success += 1
                    print(f"\n{attr_up_name} of metamon {my_monster_token_id} +{upper_num}: {attr_num} -> {upper_attr_num}")
                    print(f"Score of metamon {my_monster_token_id}: {sca} -> {upper_sca}")
            else:
                print(f"\nUp {attr_up_name} for metamon {my_monster_token_id} unsuccesful")

        tbar.set_description("Fighting...")
        
        for _ in tbar:
            payload = {
                "monsterA": my_monster_id,
                "monsterB": target_monster_id,
                "address": self.address,
                "battleLevel": battle_level,
            }
            headers = {
                "accessToken": self.token,
            }
            response = post_formdata(payload, START_FIGHT_URL, headers)

            code = response.get("code")
            if code == "BATTLE_NOPAY":
                self.no_enough_money = True
                break
            
            data = response.get("data", {})
            challenge_monster = data.get("challengedMonster")
            challenge_record = data.get("challengeRecords")
            fight_result = data.get("challengeResult", False)
            bp_fragment_num = data.get("bpFragmentNum", 10)
            
            target_monster_id = challenge_monster.get("id")
            target_monster_luk = challenge_monster.get("luk")
            target_monster_size = challenge_monster.get("con")
            target_monster_inte = challenge_monster.get("inte")
            target_monster_crg = challenge_monster.get("crg")
            target_monster_inv = challenge_monster.get("inv")
            target_monster_sca = challenge_monster.get("sca")
            target_monster_race = challenge_monster.get("race")
            opp_crit_count = 0           
            if self.battle_record:
                opp_crit_count = self.display_battle(challenge_record,challenge_monster, my_monster_id, my_size, my_inv, my_courage, my_inte)
                
            if self.auto_lvl_up:
                # Try to lvl up
                res = post_formdata({"nftId": my_monster_id, "address": self.address},
                                    LVL_UP_URL,
                                    headers)
                code = res.get("code")
                if code == "SUCCESS":
                    tbar.set_description("LVL UP successful! Continue fighting...")
                    my_level += 1
                    # Update league level if new level is 21 or 41
                    battle_level = pick_battle_level(my_level)

            self.total_bp_num += bp_fragment_num
            total_bp_fragment_num += bp_fragment_num
            if fight_result:
                success += 1
                self.total_success += 1
            else:
                fail += 1
                self.total_fail += 1

        mtm_stats.append({
            "TokenId": my_monster_token_id,
            "Race": my_race,
            "Power": my_power,
            "Level": my_level,
            "Size": my_size,
            "Wisdom": my_inte,
            "Courage": my_courage,
            "Luck": my_luk,
            "Stealth": my_inv,
            "Opp TokenId": target_monster_id,
            "Opp Race": target_monster_race,
            "Opp Luk": target_monster_luk,
            "Opp Courage": target_monster_crg,
            "Opp Wisdom": target_monster_inte,
            "Opp Size": target_monster_size,
            "Opp Stealth": target_monster_inv,
            "Opp Power": target_monster_sca,
            "Opp Crit Times": opp_crit_count,
            "Total battles": loop_count,
            "Victories": success,
            "Defeats": fail,
            "Total egg shards": total_bp_fragment_num,
            "Timestamp": datetime_now(),
        })
        mtm_stats_print = []
        mtm_stats_print.append({
            "MonId": my_monster_token_id,
            "Race": my_race,
            "Power": my_power,
            "Level": my_level,
            "Total battles": loop_count,
            "Victories": success,
            "Defeats": fail,
            "Total egg shards": total_bp_fragment_num,
            "Timestamp": datetime_now(),
        })
        mtm_stats_df = pd.DataFrame(mtm_stats)
        print(f"{mtm_stats_print}")
        self.mtm_stats_df.append(mtm_stats_df)

    def get_wallet_properties(self):
        """ Obtain list of metamons on the wallet"""

        payload = {"address": self.address}
        headers = {
            "accesstoken": self.token,
        }
        response = post_formdata(payload, WALLET_PROPERTY_LIST, headers)
        mtms = response.get("data", {}).get("metamonList", [])
        return mtms

    def list_monsters(self):
        """ Obtain list of metamons on the wallet (deprecated)"""
        payload = {"address": self.address, "page": 1, "pageSize": 150, "payType": -6}
        headers = {"accessToken": self.token}
        response = post_formdata(payload, LIST_MONSTER_URL, headers)
        monsters = response.get("data", {}).get("data", {})
        return monsters

    def battle(self, w_name=None):
        """ Main method to run all battles for the day"""
        if w_name is None:
            w_name = self.address

        summary_file_name = f"{w_name}_summary.tsv"
        mtm_stats_file_name = f"{w_name}_stats.tsv"
        self.init_token()

        self.get_wallet_properties()
        monsters = self.list_monsters()
        wallet_monsters = self.get_wallet_properties()

        available_monsters = [
            monster for monster in wallet_monsters if monster.get("tear") > 0
        ]
        stats_l = []
        print(f"Available Monsters : {len(available_monsters)}")
       
        for monster in available_monsters:
            monster_id = monster.get("id")
            tear = monster.get("tear")
            level = monster.get("level")
            battlers = self.list_battlers(monster_id)
            ofm = self.other_fighting_mode
            battler = picker_battler(battlers, ofm)
            target_monster_id = battler.get("id")
            target_monster_race = battler.get("race")
            target_monster_size = battler.get("con")
            target_monster_luk = battler.get("luk")
            target_monster_inv = battler.get("inv")
            target_monster_crg = battler.get("crg")
            target_monster_inte = battler.get("inte")
            target_monster_sca = battler.get("sca")
            
            self.change_fighter(monster_id)

            self.start_fight(monster,
                             target_monster_id,
                             target_monster_race,
                             target_monster_size,
                             target_monster_luk,
                             target_monster_inv,
                             target_monster_crg,
                             target_monster_inte,
                             target_monster_sca,
                             loop_count=tear)
            if self.no_enough_money:
                print("Not enough u-RACA")
                break
        total_count = self.total_success + self.total_fail
        success_percent = .0
        if total_count > 0:
            success_percent = (self.total_success / total_count) * 100

        success_powup_percent = .0
        total_powup_count = self.total_powup_success + self.total_powup_fail
        if total_powup_count > 0:
            success_powup_percent = (self.total_powup_success / total_powup_count) * 100        
        if total_count <= 0:
            print("No battles to record")
            return

        stats_l.append({
            "Victories": self.total_success,
            "Defeats": self.total_fail,
            "Win Rate": f"{success_percent:.2f}%",
            "Total Egg Shards": self.total_bp_num,
            "Powerup Success Rate": f"{success_powup_percent: .2f}%",
            "Datetime": datetime_now()
        })

        stats_df = pd.DataFrame(stats_l)
        print(stats_df)
        if os.path.exists(summary_file_name) and self.output_stats:
            back_fn = f"{summary_file_name}.bak"
            os.rename(summary_file_name, back_fn)
            tmp_df = pd.read_csv(back_fn, sep="\t", dtype="str")
            stats_upd_df = pd.concat([stats_df, tmp_df])
            stats_df = stats_upd_df
            os.remove(back_fn)

        if self.output_stats:
            stats_df.to_csv(summary_file_name, index=False, sep="\t")

        mtm_stats_df = pd.concat(self.mtm_stats_df)
        if os.path.exists(mtm_stats_file_name) and self.output_stats:
            back_fn = f"{mtm_stats_file_name}.bak"
            os.rename(mtm_stats_file_name, back_fn)
            tmp_df = pd.read_csv(back_fn, sep="\t", dtype="str")
            upd_df = pd.concat([mtm_stats_df, tmp_df])
            mtm_stats_df = upd_df
            os.remove(back_fn)
        if self.output_stats:
            mtm_stats_df.to_csv(mtm_stats_file_name, sep="\t", index=False)

    def mint_eggs(self):
        self.init_token()

        headers = {
            "accessToken": self.token,
        }
        payload = {"address": self.address}

        # Check current egg fragments
        check_bag_res = post_formdata(payload, CHECK_BAG_URL, headers)
        items = check_bag_res.get("data", {}).get("item")
        total_egg_fragments = 0

        for item in items:
            if item.get("bpType") == 1:
                total_egg_fragments = item.get("bpNum")
                break

        total_egg = int(int(total_egg_fragments) / 1000)

        if total_egg < 1:
            print("You don't have enough egg fragments to mint")
            return

        # Mint egg
        res = post_formdata(payload, MINT_EGG_URL, headers)
        code = res.get("code")
        if code != "SUCCESS":
            print("Mint eggs failed!")
            return

        print(f"Minted Eggs Total: {total_egg}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--input-tsv", help="Path to tsv file with wallets' "
                                                  "access records (name, address, sign, login message) "
                                                  "name is used for filename with table of results. "
                                                  "Results for each wallet are saved in separate files",
                        default="wallets.tsv", type=str)
    parser.add_argument("-nl", "--no-lvlup", help="Disable automatic lvl up "
                                                  "(if not enough potions/diamonds it will be disabled anyway) "
                                                  "by default lvl up will be attempted after each battle",
                        action="store_true", default=False)
    parser.add_argument("-nb", "--skip-battles", help="No battles, use when need to only mint eggs from shards",
                        action="store_true", default=False)
    parser.add_argument("-e", "--mint-eggs", help="Automatically mint eggs after all battles done for a day",
                        action="store_true", default=False)
    parser.add_argument("-s", "--save-results", help="To enable saving results on disk use this option. "
                                                     "Two files <name>_summary.tsv and <name>_stats.tsv will "
                                                     "be saved in current dir.",
                        action="store_true", default=False)
                        
    parser.add_argument("-ofm", "--other-fighting-mode", help="To select metamon have lowest Wisdom, Size, Luck, Courage, Stealth to play for more win",
                        action="store_true", default=False)
    parser.add_argument("-ls", "--lowest-score", help="To select metamon have lowest score by hardcode metamon id",
                        action="store_true", default=False)                      
    parser.add_argument("-expup", "--auto-exp-up", help="Automatically up exp for metamon before battle",
                        action="store_true", default=False)
    parser.add_argument("-powerup", "--auto-power-up", help="Automatically up power for metamon before battle",
                        action="store_true", default=False)
    parser.add_argument("-br","--battle-record", help="Creating log for metamons battle",
                        action="store_true", default=False)                        
                        
    args = parser.parse_args()

    if not os.path.exists(args.input_tsv):
        print(f"Input file {args.input_tsv} does not exist")
        sys.exit(-1)

    # determine delimiter char from given input file
    with open(args.input_tsv) as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.readline(), "\t ;,")
        delim = dialect.delimiter

    wallets = pd.read_csv(args.input_tsv, sep=delim)

    auto_lvlup = not args.no_lvlup
    auto_powerup = args.auto_power_up
    auto_expup = args.auto_exp_up
    other_fmode = args.other_fighting_mode
    lscore = args.lowest_score
    for i, r in wallets.iterrows():
        mtm = MetamonPlayer(address=r.address,
                            sign=r.sign,
                            msg=r.msg,
                            auto_lvl_up=auto_lvlup,
                            other_fighting_mode =other_fmode,
                            lowest_score = lscore,
                            auto_exp_up = auto_expup,
                            auto_power_up = auto_powerup,
                            battle_record = args.battle_record
                            output_stats=args.save_results)

        if not args.skip_battles:
            mtm.battle(w_name=r["name"])
        else:
            if args.auto_exp_up:
                mtm.auto_up_exp()
            if args.auto_power_up:
                mtm.auto_up_power()
        if args.mint_eggs:
            mtm.mint_eggs()
           