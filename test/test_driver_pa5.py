#!/usr/bin/env python3
"""
Auto-grading driver for CSC 435 Programming Assignment 5
Detects the programming language used in the submission by reading line 5 of README.md
"""

import subprocess
import os
import shutil
import random
import threading
import time
import re

# Constants for file paths
QUERIES_A_PATH = "../tests/traces/queries-a.txt"
QUERIES_B_PATH = "../tests/traces/queries-b.txt"
QUERIES_C_PATH = "../tests/traces/queries-c.txt"
DATASET_BASE_PATH = "../datasets/dataset1_client_server"
LOGS_DIR = 'tests/logs'
TRACES_DIR = 'tests/traces'
README_PATH = 'README.md'
APP_JAVA_DIR = 'app-java'
APP_CPP_DIR = 'app-cpp'
BUILD_DIR = 'build'
JAVA_JAR_PATH = "target/app-java-1.0-SNAPSHOT.jar"
JAVA_SERVER_CLASS = "csc435.app.FileRetrievalServer"
JAVA_CLIENT_CLASS = "csc435.app.FileRetrievalClient"
CPP_SERVER_EXE = "./build/file-retrieval-server"
CPP_CLIENT_EXE = "./build/file-retrieval-client"
SERVER_PORT = "12345"
NUM_THREADS = "4"

def detect_programming_language():
    """
    Reads line 5 from README.md and extracts the programming language.
    
    Returns:
        str: 'Java', 'C++', 'Both', or 'Unknown' if not detected
    """
    print(f"Detecting programming language ...")
    
    try:
        with open(README_PATH, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            
            # Find the line containing "Solution programming language"
            target_line = None
            for line in lines:
                if "Solution programming language" in line:
                    target_line = line.strip()
                    break
            
            if target_line is None:
                return 'Unknown'
            
            # Check for Java and C++ in the target line
            has_java = 'Java' in target_line
            has_cpp = 'C++' in target_line
            
            if has_java and has_cpp:
                return 'Both'
            elif has_java:
                return 'Java'
            elif has_cpp:
                return 'C++'
            else:
                return 'Unknown'
                
    except FileNotFoundError:
        print("Error: README.md not found")
        return 'Unknown'
    except Exception as e:
        print(f"Error reading README.md: {e}")
        return 'Unknown'

def load_queries(file_path, num_samples, total_range):
    """
    Load and sample queries from a file.
    
    Args:
        file_path (str): Path to the queries file.
        num_samples (int): Number of samples to select.
        total_range (int): Total range to sample from.
    
    Returns:
        tuple: (queries list, selected indices list)
    """
    queries = []
    with open(file_path, "r") as file:
        for line in file:
            queries.append(line.strip())  # Strip to remove newlines
    selected_indices = random.sample(range(total_range), num_samples)
    return queries, selected_indices

class ClientInstance:
    def __init__(self, exe_command, client_id, num_clients, dataset_base):
        self.client_id = client_id
        if num_clients == 1:
            folder_name = "1_client"
        else:
            folder_name = f"{num_clients}_clients"
        self.dataset_path = f"{dataset_base}/{folder_name}/client_{client_id}"
        
        self.proc = subprocess.Popen(
            exe_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        self.output = []
        self.indexing_done = threading.Event()
        self.reader_thread = threading.Thread(target=self._read_stdout)
        self.reader_thread.start()

    def _read_stdout(self):
        try:
            while True:
                if self.proc.stdout is None:
                    break
                line = self.proc.stdout.readline()
                if not line:
                    break
                self.output.append(line)
                if "Completed indexing" in line:
                    self.indexing_done.set()
        except:
            pass

    def send_command(self, cmd):
        if self.proc.poll() is None:
            try:
                if self.proc.stdin is not None:
                    self.proc.stdin.write(cmd + "\n")
                    self.proc.stdin.flush()
            except BrokenPipeError:
                pass

    def wait_for_output(self, pattern, timeout=5):
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_out = "".join(self.output)
            if pattern in current_out:
                return True
            time.sleep(0.1)
        return False

    def close(self):
        self.send_command("quit")
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        
        self.reader_thread.join(timeout=2)
        return "".join(self.output)

def parse_output_and_log(cmd_output, search_terms, selected_a, selected_b, selected_c):
    """
    Parse the command output and log results to files.
    
    Args:
        cmd_output (str): Output from the subprocess.
        search_terms (list): List of search terms.
        selected_a, selected_b, selected_c: Lists of selected indices.
    """
    if os.path.exists(f"../{LOGS_DIR}"):
        shutil.rmtree(f"../{LOGS_DIR}")
    os.makedirs(f"../{LOGS_DIR}")

    query_outputs = []
    current_output = []

    for line in cmd_output.splitlines():
        if line.startswith("> "):
            if current_output:
                query_outputs.append(current_output)
            current_output = [line[2:]]
            continue
        if current_output is not None:
            current_output.append(line)

    if current_output:
        query_outputs.append(current_output)
    
    search_term_index = 0
    term_index = 0
    section = 'a'
    section_indices = {'a': selected_a, 'b': selected_b, 'c': selected_c}
    section_limits = {'a': 2, 'b': 4, 'c': 4}
    
    # Filter only outputs that correspond to search commands
    search_outputs = [out for out in query_outputs if out and out[0].startswith("Search")]

    for output in search_outputs:
        current_results = ""

        for i, line in enumerate(output):
            if line.startswith("Search results"):
                result_count = min(int(line.split(" ")[6].split(")")[0]), 10)
                start = i + 1
                end = min(start + result_count, len(output))
                results_lines = output[start:end]
                if results_lines:
                    current_results = "\n".join(results_lines) + "\n"
                else:
                    current_results = ""
                break

        indices = section_indices[section]
        query_index = indices[term_index % len(indices)]
        with open(f"../{LOGS_DIR}/query-{section}-{query_index}.txt", "w") as file:
            file.write(f"{search_terms[search_term_index]}\n")
            file.write(current_results)

        with open(f"../{LOGS_DIR}/output-{section}-{query_index}.txt", "w") as file:
            if output:
                file.write("\n".join(output) + "\n")
            else:
                file.write("")

        term_index += 1
        search_term_index += 1
        if term_index == section_limits[section]:
            if section == 'a':
                section = 'b'
            elif section == 'b':
                section = 'c'
            term_index = 0

def check_outputs(num_clients, selected_a, selected_b, selected_c, queries_a, queries_b, queries_c, points_per_query):
    """
    Check if the log outputs match the trace outputs for each query and calculate score.
    
    Args:
        selected_a, selected_b, selected_c: Lists of selected indices.
        queries_a, queries_b, queries_c: Lists of query strings.
    """
    sections = {'a': selected_a, 'b': selected_b, 'c': selected_c}
    queries = {'a': queries_a, 'b': queries_b, 'c': queries_c}
    score = 0
    i = 0
    
    for section, indices in sections.items():
        for index in indices:
            log_file = f"{LOGS_DIR}/query-{section}-{index}.txt"
            output_file = f"{LOGS_DIR}/output-{section}-{index}.txt"
            trace_file = f"{TRACES_DIR}/query-{section}-{index}.txt"
            
            try:
                with open(f"../{log_file}", 'r') as lf:
                    log_lines = lf.readlines()
                with open(f"../{trace_file}", 'r') as tf:
                    trace_lines = tf.readlines()
                
                log_results = []
                for line in log_lines:
                    line = line.strip()
                    if line.startswith('*'):
                        m = re.search(r"client(\d+):.*?(folder\d+/.*:\d+)$", line)
                        if m:
                            log_results.append(f"client{m.group(1)}:{m.group(2)}")
                        else:
                            log_results.append(line)

                trace_results = []
                for line in trace_lines:
                    line = line.strip()
                    if line.startswith('*'):
                        m = re.search(r"(folder(\d+)/.*:\d+)$", line)
                        if m:
                            tail = m.group(1)
                            folder_num = int(m.group(2))
                            expected_client = (folder_num - 1) // (8 // num_clients) + 1
                            trace_results.append(f"client{expected_client}:{tail}")
                        else:
                            trace_results.append(line)
                
                if log_results == trace_results:
                    score += points_per_query
                    query_cmd = queries[section][index]
                    print(f"{i}. Query '{query_cmd}': Output matches trace. +{points_per_query} points.")
                else:
                    query_cmd = queries[section][index]
                    print(f"{i}. Query '{query_cmd}': Output does not match trace.")
                    print(f"  -> Log File: {log_file}, Trace File: {trace_file}")
                    print(f"  -> Processed Log Results:\n" + "\n".join(log_results))
                    print(f"  -> Processed Trace Results:\n" + "\n".join(trace_results))
            except FileNotFoundError as e:
                print(f"Query {section}-{index}: File not found - {e}")
            except Exception as e:
                print(f"Query {section}-{index}: Error comparing outputs - {e}")
            i += 1
    
    max_score = (len(selected_a) + len(selected_b) + len(selected_c)) * points_per_query
    print(f"Total score: {score}/{max_score}")
    
    return score

def grade_scenario(num_clients, server_exe, client_exe, selected_a, selected_b, selected_c, queries_a, queries_b, queries_c, points_per_query):
    """
    Runs a test scenario with a specific number of clients.
    """
    print(f"\n--- Running Test with {num_clients} Client(s) ---")

    # Start Server
    server_proc = subprocess.Popen(
        server_exe,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Give server a moment to start
    time.sleep(2)
    
    clients = []
    for i in range(1, num_clients + 1):
        client = ClientInstance(client_exe, i, num_clients, DATASET_BASE_PATH)
        clients.append(client)
        
        # Connect and check ID
        client.send_command(f"connect 127.0.0.1 {SERVER_PORT}")
        client.send_command("get_info")
        if client.wait_for_output(f"client ID: {i}", timeout=5):
            print(f"Client {i} connected and verified ID: {i}")
        else:
            print(f"Error: Client {i} did not receive ID {i}.")

    # Index
    for client in clients:
        client.send_command(f"index {client.dataset_path}")

    # Wait for indexing to complete
    for client in clients:
        if not client.indexing_done.wait(timeout=120):
            print(f"Timeout waiting for Client {client.client_id} to index.")

    print("Indexing completed by all clients.")

    # Search (Client 1 only)
    search_terms = []
    for i in selected_a:
        clients[0].send_command(f"search {queries_a[i]}")
        search_terms.append(f"search {queries_a[i]}")
    for i in selected_b:
        clients[0].send_command(f"search {queries_b[i]}")
        search_terms.append(f"search {queries_b[i]}")
    for i in selected_c:
        clients[0].send_command(f"search {queries_c[i]}")
        search_terms.append(f"search {queries_c[i]}")

    # Close Clients
    c1_out = clients[0].close()
    for client in clients[1:]:
        client.close()

    # Stop Server
    try:
        server_proc.communicate(input="quit\n", timeout=5)
    except:
        server_proc.kill()
        
    # Parse output and log
    parse_output_and_log(c1_out, search_terms, selected_a, selected_b, selected_c)
    
    # Check outputs against traces
    return check_outputs(num_clients, selected_a, selected_b, selected_c, queries_a, queries_b, queries_c, points_per_query)

def grade_java():
    """
    Function to grade the Java program.
    """
    print(f"Running autograder for Java program ...")
    
    server_exe = ["java", "-cp", JAVA_JAR_PATH, JAVA_SERVER_CLASS, SERVER_PORT]
    client_exe = ["java", "-cp", JAVA_JAR_PATH, JAVA_CLIENT_CLASS]
    
    # Load queries
    queries_a, selected_a = load_queries(QUERIES_A_PATH, 2, 20)
    queries_b, selected_b = load_queries(QUERIES_B_PATH, 4, 20)
    queries_c, selected_c = load_queries(QUERIES_C_PATH, 4, 10)
    
    total_score = 0
    total_score += grade_scenario(1, server_exe, client_exe, selected_a, selected_b, selected_c, queries_a, queries_b, queries_c, 1)
    total_score += grade_scenario(2, server_exe, client_exe, selected_a, selected_b, selected_c, queries_a, queries_b, queries_c, 2)
    total_score += grade_scenario(4, server_exe, client_exe, selected_a, selected_b, selected_c, queries_a, queries_b, queries_c, 2)
    
    print(f"\nFinal Total Score: {total_score}/50")

def grade_cpp():
    """
    Function to grade the C++ program.
    """
    print(f"Running autograder for C++ program ...")
    
    server_exe = [CPP_SERVER_EXE, SERVER_PORT]
    client_exe = [CPP_CLIENT_EXE]
    
    # Load queries
    queries_a, selected_a = load_queries(QUERIES_A_PATH, 2, 20)
    queries_b, selected_b = load_queries(QUERIES_B_PATH, 4, 20)
    queries_c, selected_c = load_queries(QUERIES_C_PATH, 4, 10)
    
    total_score = 0
    total_score += grade_scenario(1, server_exe, client_exe, selected_a, selected_b, selected_c, queries_a, queries_b, queries_c, 1)
    total_score += grade_scenario(2, server_exe, client_exe, selected_a, selected_b, selected_c, queries_a, queries_b, queries_c, 2)
    total_score += grade_scenario(4, server_exe, client_exe, selected_a, selected_b, selected_c, queries_a, queries_b, queries_c, 2)
    
    print(f"\nFinal Total Score: {total_score}/50")

def test_java():
    """
    Function to test the Java program.
    """
    
    print(f"Compiling Java program ...")
    
    try:
        # Change to the app-java directory
        os.chdir(APP_JAVA_DIR)
        
        # Run mvn clean
        result_clean = subprocess.run("mvn clean", shell=True, capture_output=True, text=True)
        if result_clean.returncode != 0:
            print("Error: Maven clean failed.")
            print("STDOUT:", result_clean.stdout)
            print("STDERR:", result_clean.stderr)
            return
        
        # Run mvn compile
        result_compile = subprocess.run("mvn compile", shell=True, capture_output=True, text=True)
        if result_compile.returncode != 0:
            print("Error: Maven compile failed.")
            print("STDOUT:", result_compile.stdout)
            print("STDERR:", result_compile.stderr)
            return
        
        # Run mvn package
        result_package = subprocess.run("mvn package", shell=True, capture_output=True, text=True)
        if result_package.returncode != 0:
            print("Error: Maven package failed.")
            print("STDOUT:", result_package.stdout)
            print("STDERR:", result_package.stderr)
            return
        
        print("Java program compiled and packaged successfully.")
        grade_java()
                
    except Exception as e:
        print(f"Error during Java testing: {e}")
        return

def test_cpp():
    """
    Function to test the C++ program.
    """
    
    print(f"Compiling C++ program ...")
    
    try:
        # Change to the app-cpp directory
        os.chdir(APP_CPP_DIR)
        
        # Create build directory if not exists, clean if exists
        if os.path.exists(BUILD_DIR):
            shutil.rmtree(BUILD_DIR)
        os.makedirs(BUILD_DIR)
        
        # Run cmake configure
        result_configure = subprocess.run(f"cmake -S . -B {BUILD_DIR}", shell=True, capture_output=True, text=True)
        if result_configure.returncode != 0:
            print("Error: CMake configure failed.")
            print("STDOUT:", result_configure.stdout)
            print("STDERR:", result_configure.stderr)
            return
        
        # Run cmake build
        result_build = subprocess.run(f"cmake --build {BUILD_DIR} --config Release", shell=True, capture_output=True, text=True)
        if result_build.returncode != 0:
            print("Error: CMake build failed.")
            print("STDOUT:", result_build.stdout)
            print("STDERR:", result_build.stderr)
            return
        
        print("C++ program compiled successfully.")
        grade_cpp()
                
    except Exception as e:
        print(f"Error during C++ testing: {e}")
        return

def main():
    language = detect_programming_language()
    
    if language == 'Unknown':
        print("Error: Programming language not found or not recognized in README.md")
        exit(1)
    elif language == 'Java':
        print(f"Successfully detected programming language: {language}")
        test_java()
    elif language == 'C++':
        print(f"Successfully detected programming language: {language}")
        test_cpp()
    elif language == 'Both':
        print("Error: Both Java and C++ are mentioned in README.md. Please specify only one programming language.")
        exit(1)

if __name__ == "__main__":
    main()
