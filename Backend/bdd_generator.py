import atlassian.errors
import requests
from atlassian import Confluence
import yaml
import abc
import re
import os
import errors
from enum import Enum
from flask import Flask, request
from unicodedata import normalize
import json

app = Flask(__name__)

@app.route('/generate-data', methods=['GET', 'POST'])
def generate_data():
    try:
        data = sg.get_requirements(request.args.get("space"), request.args.get("page"))
        if data is None:
            response = ef.generate_generic_error()
        else:
            if request.args.get("operation") == "new":
                response = cg.generate_new_scenarios(data)
            elif request.args.get("operation") == "update":
                response = cg.update_existing_scenarios(data, request.args.get("file_text"))[0]
    except errors.PageNotFoundError:
        response = ef.generate_page_not_found_error()
    except errors.CredentialsError:
        response = ef.generate_credentials_error()
    except errors.ConfluenceError:
        response = ef.generate_confluence_error()
    except errors.InvalidSpaceError:
        response = ef.generate_invalid_space_error()
    except errors.ScenariosNotFoundError:
        response = ef.generate_no_scenarios_error()
    except errors.ScenarioStatementsMissingError:
        response = ef.generate_missing_statement_error()
    except errors.ProxyEnvError:
        response = ef.generate_proxy_env_error()
    except FileExistsError:
        response = ef.generate_error_string("File already exists")
    return response


class ScenarioGetter():
    def __init__(self):
        # Open config file to get Confluence credentials
        config_path = os.path.join(os.path.dirname(__file__), 'Config/Credentials.yaml')
        with open(config_path, 'r') as config:
            config_data = yaml.safe_load(config)
            self._confluence = Confluence(
                url=config_data["url"],
                username=config_data["username"],
                password=config_data["password"]
            )

    def check_page_exists(self, page, space):
        """
        Takes a Confluence space key and page name and returns a
        boolean indicating whether the page exists in the space in Confluence

        Parameters:
            page (str): a Confluence page name
            space (str): the key of a Confluence space

        Returns:
            bool
        """

        try:
            # Check page exists in space in Confluence
            page_found = self._confluence.page_exists(space, page)
            return page_found
        # Exception can be caused by invalid credentials, for example
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                raise errors.CredentialsError
            else:
                raise errors.ConfluenceError
        except atlassian.errors.ApiPermissionError:
            raise errors.InvalidSpaceError

    def parse_response_data(self, response):
        scenarios = []
        bdd_keywords_regex = "SCENARIO|GIVEN|WHEN|THEN|AND_GIVEN|AND_WHEN|AND_THEN"

        # Loop through every scenario on the page
        for sc in response:
            last_bdd_header = 0
            scenario = {"id": sc["key"], "statements": []}
            scenario_index = next(i for i, item in enumerate(sc["properties"]) if item["key"] == "Scenario")

            # Loop through all the BDD statements within the scenario
            for j, curr_statement in enumerate(sc["properties"][scenario_index]["indexation"]["multivalues"]):

                # Skip if text is only whitespace or no text at all
                if str.isspace(curr_statement) or not curr_statement:
                    continue

                curr_statement = curr_statement.replace("\"", "")

                # Remove \xa0 (non-breaking space) character from string
                curr_statement = normalize('NFKD', curr_statement)

                statement = {"bdd_type": "", "text": ""}

                bdd_header = re.search(bdd_keywords_regex, curr_statement)

                if bdd_header:
                    statement["bdd_type"] = curr_statement[bdd_header.start():bdd_header.end()].title()
                    last_bdd_header = j

                    match = re.search("\(.*?\)",curr_statement)
                    if match:
                        # There is an edge case where there is no closing bracket but regex still works due to brackets
                        # used within the statement text. In this case, just use the whole string
                        if curr_statement.count("(") != curr_statement.count(")"):
                            statement["text"] = curr_statement[bdd_header.end() + 1:]
                        else:
                            statement["text"] = curr_statement[match.start()+1:match.end()-1]
                    else:
                        statement["text"] = curr_statement[bdd_header.end()+1:]
                    scenario["statements"].append(statement)
                else:
                    scenario["statements"][last_bdd_header]["text"] += " \\ \n" + curr_statement
            scenarios.append(scenario)
        return scenarios

    def get_requirements(self, space, page):
        """
        Takes a Confluence space key and page name and, if found, returns a list of all BDD scenarios
        stored on the page

        Parameters:
            space (str): the key of a Confluence space
            page (str): a Confluence page name

        Returns:
            list
        """

        if os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY"):
            raise errors.ProxyEnvError
        try:
            # page_found = self.check_page_exists(page, space)
            page_found = True
            if not page_found:
                raise errors.PageNotFoundError
        except errors.CredentialsError:
            raise
        except errors.ConfluenceError:
            raise
        except errors.InvalidSpaceError:
            raise

        try:
            # page_id = self._confluence.get_page_id(space, page)
            pass
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                raise errors.CredentialsError
            else:
                raise errors.ConfluenceError

        # URL required for accessing requirements in the page
        # Not used for uni project as mock data is used
        # url = self._confluence.url + '/rest/reqs/1/requirement2/' + space

        # params = {
        #     "Accept": 'application/json',
        #     "spaceKey": space,
        #     "q": "page = " + page_id
        # }

        # response = requests.get(url,
        #                         params,
        #                         auth=requests.auth.HTTPBasicAuth(self._confluence.username, self._confluence.password))

        # if response.status_code == 401:
        #     raise errors.CredentialsError

        # response_data = response.json()['results']
        
        mock_data = [
            {
                'key': 'SCEN-1',
                'properties': [
                    {
                        'key': 'Scenario',
                        'indexation':
                            {
                                'multivalues': 
                                [
                                    'SCENARIO("Mock scenario 1")',
                                    'GIVEN("Mock GIVEN statement for scenario 1")',
                                    'WHEN("Mock WHEN statement for scenario 1")',
                                    'THEN("Mock THEN statement for scenario 1")'
                                ]
                            }
                    }
                ]
            },
            {
                'key': 'SCEN-2',
                'properties': [
                    {
                        'key': 'Scenario',
                        'indexation': 
                            {
                                'multivalues': [
                                    'SCENARIO("Mock scenario 2")',
                                    'GIVEN("Mock GIVEN statement for scenario 2")',
                                    'WHEN("Mock WHEN statement for scenario 2")',
                                    'THEN("Mock THEN statement for scenario 2")'
                                ]
                            }
                    }
                ]
            },
            {
                'key': 'SCEN-3',
                'properties': [
                    {
                        'key': 'Scenario',
                        'indexation': 
                        {
                            'multivalues': [
                                'SCENARIO("Mock scenario 3")',
                                'GIVEN("Mock GIVEN statement for scenario 3")',
                                'WHEN(Mock WHEN statement for scenario 3")',
                                'THEN("Mock THEN statement for scenario 3")'
                            ]
                        }
                    }
                ]
            },
            {
                'key': 'SCEN-4',
                'properties': [
                        {
                            'key': 'Scenario',
                            'indexation': 
                            {
                                'multivalues': [
                                    'SCENARIO("Mock scenario 4")',
                                    'GIVEN("Mock GIVEN statement for scenario 4")',
                                    'WHEN("Mock WHEN statement for scenario 4")',
                                    'THEN("Mock THEN statement for scenario 4")'
                                ]
                            }
                    }
                ]
            }
        ]

        response_data = mock_data

        if len(response_data) == 0:
            raise errors.ScenariosNotFoundError

        # If a scenario in the "Requirements" page on Confluence has BDD statements, then scenario_data should contain
        # "Scenario" data structure for each scenario
        for scenario in response_data:
            if next((x for x in scenario['properties'] if x['key'] == 'Scenario'), None) is None:
                raise errors.ScenarioStatementsMissingError

        scenario_data = self.parse_response_data(response_data)
        return scenario_data

class ScenarioStatus(Enum):
    MISSING = 1
    UPDATED = 2
    UNCHANGED = 3

class CodeGenerator(abc.ABC):

    def __init__(self):
        super().__init__()

    @abc.abstractmethod
    def generate_new_scenarios(self, scenarios):
        pass

    @abc.abstractmethod
    def update_existing_scenarios(self, scenarios, existing):
        pass


class Catch2CodeGenerator(CodeGenerator):
    def __init__(self):
        super().__init__()
        self.bdd_info = {
            'scenario': {'header': 'SCENARIO', 'text': '("%text% %id%", "[%id%]")'},
            'scenario_method': {'header': 'SCENARIO_METHOD', 'text': '("%text% %id%", "[%id%]")'},
            'given': {'header': 'GIVEN', 'text': '("%text%")'},
            'and_given': {'header': 'AND_GIVEN', 'text': '("%text%")'},
            'when': {'header': 'WHEN', 'text': '("%text%")'},
            'and_when': {'header': 'AND_WHEN', 'text': '("%text%")'},
            'then': {'header': 'THEN', 'text': '("%text%")'},
            'and_then': {'header': 'AND_THEN', 'text': '("%text%")'}
        }
        self.tab = "    "

    def write_scenarios_to_file(self, scenarios, path):
        if os.path.isfile(path):
            raise FileExistsError
        file_text = self.generate_new_scenarios(scenarios)
        with open(path, 'w') as f:
            f.write(file_text)

    def generate_new_scenarios(self, scenarios):
        file_text = ""
        for scenario in scenarios:
            file_text += self.construct_nested_statements(self.get_scenario_code(scenario["statements"], scenario["id"]), 0)
        return file_text.rstrip()

    def write_scenario(self, scenario, tab_level):
        text = ""
        scenario_code = self.get_scenario_code(scenario["statements"], scenario["id"])
        for statement in scenario_code:
            text += self.tab * tab_level + statement
            text += "\n" + self.tab * tab_level + "{\n"
            tab_level += 1
        for _ in scenario_code:
            text += self.tab * (tab_level - 1) + "}\n"
            tab_level -= 1
        return text

    def update_existing_file(self, scenarios, path):
        try:
            with open(path, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            raise

        lines_string = ''.join(lines)

        lines_string, updated_scenarios, missing_scenarios, unchanged_scenarios = self.update_existing_scenarios(scenarios, lines_string)

        with open(path, 'w') as f:
            f.write(lines_string)

        return updated_scenarios, missing_scenarios, unchanged_scenarios

    def update_existing_scenarios(self, scenarios, existing):
        lines_string = existing

        # First, auto replace any \t tabs with four spaces
        lines_string = lines_string.replace("\t", "    ")

        updates_scenarios = []
        missing_scenarios = []
        unchanged_scenarios = []

        for scenario in scenarios:
            status, updated_file_string = self.update_scenario_code(scenario, lines_string)
            if status == ScenarioStatus.UPDATED:
                lines_string = updated_file_string
                updates_scenarios.append(scenario)
            elif status == ScenarioStatus.MISSING:
                missing_scenarios.append(scenario)
            else:
                unchanged_scenarios.append(scenario)

        for scenario in missing_scenarios:
            missing_text = self.construct_nested_statements(self.get_scenario_code(scenario["statements"], scenario["id"]))
            lines_string = self.insert_after_last_scenario(lines_string, missing_text).rstrip()
        return lines_string, updates_scenarios, missing_scenarios, unchanged_scenarios

    def get_scenario_code(self, scenario, id):
        code = []
        for statement in scenario:
            code.append(self.bdd_info[str(statement["bdd_type"]).lower()]["header"] + self.bdd_info[str(statement["bdd_type"]).lower()]["text"].replace("%text%", statement["text"]).replace("%id%", id))
        return code

    def update_scenario_code(self, scenario, file_string):
        # Get code equivalents of updated scenario statements
        updated_scenario_code = self.get_scenario_code(scenario["statements"], scenario["id"])

        # Generate regex pattern of BDD headers
        bdd_headers_regex = '|'.join([x["header"] for x in self.bdd_info.values()])

        # Regex searches for the Scenario header, then some text, then the scenario ID, then some text, then either
        # the next Scenario keyword or the end of the string. Note that for the 'some text' the regex pattern ensures
        # that the Scenario header is not between the first occurence of scenario and the ID
        pattern_string = self.bdd_info["scenario"]["header"]+'(?!.*'+self.bdd_info["scenario"]["header"]+'.*'+scenario["id"]+').*?'+scenario["id"]+'.*?(?='+self.bdd_info["scenario"]["header"]+'|\Z)'
        pattern = re.compile(pattern_string, re.MULTILINE | re.DOTALL)
        scenario_match = pattern.search(file_string)

        # Scenario not in file, therefore can't update
        if not scenario_match:
            return ScenarioStatus.MISSING, ""

        # Create substring of file
        scenario_substring = file_string[scenario_match.start():scenario_match.end()]
        original = scenario_substring

        # Find all current BDD statements within scenario
        matches = re.finditer('('+bdd_headers_regex+')\(.*?\)', scenario_substring, re.MULTILINE|re.DOTALL)

        match_list = []
        for match in matches:
            match_list.append(scenario_substring[match.start():match.end()])

        # Replace each existing statement with new statement
        if len(updated_scenario_code) == len(match_list):
            for i in range(len(updated_scenario_code)):
                scenario_substring = scenario_substring.replace(match_list[i], updated_scenario_code[i])

        # Replace each existing statement with new statement, then add in additional statements
        elif len(updated_scenario_code) > len(match_list):
            for i in range(len(match_list)):
                scenario_substring = scenario_substring.replace(match_list[i], updated_scenario_code[i])

            # Find location of last statement in updated string
            last_statement = scenario_substring.find(updated_scenario_code[len(match_list)-1])

            # Get number of '{' within last BDD statement
            num_of_openings = scenario_substring[last_statement:].count('{')
            statement_start = self.find_nth_occurrence(scenario_substring[last_statement:], '{', 1)
            statement_end = self.find_nth_occurrence(scenario_substring[last_statement:], '}', num_of_openings)+1

            # Separate the last statement code block lines in a list
            statement_as_list = scenario_substring[last_statement+statement_start:last_statement+statement_end].split('\n')

            # Create the code for the new statements and insert it into the current last
            tab_level = int((len(scenario_substring[:last_statement])-len(scenario_substring[:last_statement].rstrip(" "))) / 4) + 1
            new_statements = self.construct_nested_statements(updated_scenario_code[len(match_list):], tab_level)
            statement_as_list.insert(-1, new_statements.rstrip())

            # Replace the existing last statement code with code that includes the new statements within
            new_statements = '\n'.join(statement_as_list)
            scenario_substring = scenario_substring.replace(scenario_substring[last_statement+statement_start:last_statement+statement_end], new_statements)

        # Replace some existing statements with the new ones, then remove any statements that are no longer needed
        else:
            for i in range(len(updated_scenario_code)):
                scenario_substring = scenario_substring.replace(match_list[i], updated_scenario_code[i])

            # Find the start '{' and close '}' of the last updated scenario
            last_statement = scenario_substring.find(updated_scenario_code[len(updated_scenario_code)-1])
            num_of_openings = scenario_substring[last_statement:].count('{')
            pattern = '\{.*?'*num_of_openings + '.*?\}'*num_of_openings
            statement_start_and_close = re.search(pattern, scenario_substring[last_statement:], re.MULTILINE | re.DOTALL)

            # Remove any text between the start and close of the statement
            scenario_substring = scenario_substring.replace(scenario_substring[last_statement+statement_start_and_close.start()+1:last_statement+statement_start_and_close.end()-1], "")

        if original != scenario_substring:
            file_string = file_string.replace(original, scenario_substring).rstrip()
        else:
            return ScenarioStatus.UNCHANGED, ""
        return ScenarioStatus.UPDATED, file_string

    def construct_nested_statements(self, statements, tab_level=0):
        text = ""
        for statement in statements:
            text += self.tab * tab_level + statement
            text += "\n" + self.tab * tab_level + "{\n"
            tab_level += 1
        for _ in statements:
            text += self.tab * (tab_level - 1) + "}\n"
            tab_level -= 1
        return text

    def find_nth_occurrence(self, string, substring, occurrence):
        occurrences = (i for i, l in enumerate(string) if l == substring)
        for _ in range(occurrence - 1):
            next(occurrences)
        return next(occurrences)

    def insert_after_last_scenario(self, file_string, new_string):
        # Find all current BDD statements within scenario
        matches = re.finditer('(' + self.bdd_info["scenario"]["header"] + ')\(.*?\)', file_string)
        match_list = []
        for match in matches:
            match_list.append(match.start())
        try:
            last_scenario_index = match_list[-1]
            # Get number of '{' within last BDD statement
            num_of_openings = file_string[last_scenario_index:].count('{')
            scenario_end = self.find_nth_occurrence(file_string[last_scenario_index:], '}', num_of_openings) + 1
            file_string = file_string[:last_scenario_index + scenario_end] + "\n" + new_string + file_string[last_scenario_index + scenario_end:]
        # If no other scenarios are in file, just add all scenarios to end
        except IndexError:
            file_string = file_string + new_string
        return file_string

class ErrorFormatter():
    def generate_error_string(self, text):
        error_text = "Error: {error}"
        return error_text.format(error=text)

    def add_help_url(self, text):
        url = "fake_help_url"
        return_val = "{text}\nSee {url} form more information."
        return return_val.format(text=text, url=url)

    def generate_missing_statement_error(self):
        text = "BDD statements not found for at least one scenario. Ensure the 'Ignore for properties' value in the" \
               " page RequirementsYogi macro is not ticked."
        return_val = self.generate_error_string(text)
        return_val = self.add_help_url(return_val)
        return return_val

    def generate_page_not_found_error(self):
        text = "Page not found. Ensure the page name is correct and exists in your space."
        return self.generate_error_string(text)

    def generate_invalid_space_error(self):
        text = "Cannot access space. Space name may be incorrect or you may not have access."
        return self.generate_error_string(text)

    def generate_credentials_error(self):
        text = "Unable to retrieve BDD scenarios. Ensure that your credentials are correct."
        return self.generate_error_string(text)

    def generate_no_scenarios_error(self):
        text = "No scenarios found for page. Ensure the page contains BDD scenarios."
        return self.generate_error_string(text)

    def generate_confluence_error(self):
        text = "Error when contacting Confluence."
        return self.generate_error_string(text)

    def generate_proxy_env_error(self):
        text = "Found HTTP_PROXY or HTTPS_PROXY environment variables. Either rename or delete them before using the application"
        return self.generate_error_string(text)

    def generate_generic_error(self):
        text = "Could not complete operation."
        return self.generate_error_string(text)

if __name__ == "__main__":
    sg = ScenarioGetter()
    cg = Catch2CodeGenerator()
    ef = ErrorFormatter()
    app.run(host="0.0.0.0", port=8002)