#!/usr/bin/env python3
"""
Auto-grading driver for CSC 435 Programming Assignment 2
Detects the programming language used in the submission by reading line 5 of README.md
"""

import subprocess
import os
import shutil
import random
import re

# Constants for file paths
QUERIES_A_PATH = "../tests/traces/queries-a.txt"
QUERIES_B_PATH = "../tests/traces/queries-b.txt"
QUERIES_C_PATH = "../tests/traces/queries-c.txt"
DATASET_PATH = "../datasets/dataset1"
LOGS_DIR = 'tests/logs'
TRACES_DIR = 'tests/traces'
README_PATH = 'README.md'
APP_JAVA_DIR = 'app-java'
APP_CPP_DIR = 'app-cpp'
BUILD_DIR = 'build'
JAVA_JAR_PATH = "target/app-java-1.0-SNAPSHOT.jar"
JAVA_CLASS = "csc435.app.FileRetrievalEngine"
CPP_EXE = "./build/file-retrieval-engine"

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

def build_command_input(selected_a, selected_b, selected_c, queries_a, queries_b, queries_c):
    """
    Build the command input string for the subprocess.
    
    Args:
        selected_a, selected_b, selected_c: Lists of selected indices.
        queries_a, queries_b, queries_c: Lists of query strings.
    
    Returns:
        tuple: (command input string, list of search terms)
    """
    cmd_input = f"index {DATASET_PATH}\n"
    search_terms = []
    
    for i in selected_a:
        cmd_input += f"search {queries_a[i]}\n"
        search_terms.append(f"search {queries_a[i]}")
    
    for i in selected_b:
        cmd_input += f"search {queries_b[i]}\n"
        search_terms.append(f"search {queries_b[i]}")
    
    for i in selected_c:
        cmd_input += f"search {queries_c[i]}\n"
        search_terms.append(f"search {queries_c[i]}")
    
    cmd_input += "quit\n"
    return cmd_input, search_terms

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
    result_count = -1
    current_results = ""
    section = 'a'
    section_indices = {'a': selected_a, 'b': selected_b, 'c': selected_c}
    section_limits = {'a': 10, 'b': 10, 'c': 5}

    for output in query_outputs[1:-1]:
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

def check_outputs(selected_a, selected_b, selected_c, queries_a, queries_b, queries_c):
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
                        m = re.search(r"(folder\d+/.*:\d+)$", line)
                        if m:
                            log_results.append(m.group(1))
                        else:
                            log_results.append(line)

                trace_results = []
                for line in trace_lines:
                    line = line.strip()
                    if line.startswith('*'):
                        m = re.search(r"(folder\d+/.*:\d+)$", line)
                        if m:
                            trace_results.append(m.group(1))
                        else:
                            trace_results.append(line)
                
                if log_results == trace_results:
                    score += 2
                    query_cmd = queries[section][index]
                    print(f"{i}. Query '{query_cmd}': Output matches trace. +2 points.")
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
    
    print(f"Total score: {score}/50")
    
    return score

def grade(exe_command):
    """
    Function to grade the program.
    """
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Dataset not found at {DATASET_PATH}")
        exit(1)

    # Load queries
    queries_a, selected_a = load_queries(QUERIES_A_PATH, 10, 20)
    queries_b, selected_b = load_queries(QUERIES_B_PATH, 10, 20)
    queries_c, selected_c = load_queries(QUERIES_C_PATH, 5, 10)
    
    # Build command input
    cmd_input, search_terms = build_command_input(selected_a, selected_b, selected_c, queries_a, queries_b, queries_c)
    
    # Run subprocess
    proc = subprocess.Popen(
        exe_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1)
    
    try:
        cmd_output, cmd_error = proc.communicate(input=cmd_input, timeout=(30 * 60))
    except subprocess.TimeoutExpired:
        proc.kill()
        cmd_output = ""
        cmd_error = "Process timed out."
    
    # Check for unexpected exit
    if proc.returncode != 0:
        print(f"Program exited unexpectedly with return code {proc.returncode}.")
        if cmd_error:
            print(f"Error output: {cmd_error}")
            return
    
    # Parse output and log
    parse_output_and_log(cmd_output, search_terms, selected_a, selected_b, selected_c)
    
    # Check outputs against traces
    check_outputs(selected_a, selected_b, selected_c, queries_a, queries_b, queries_c)

def grade_java():
    """
    Function to grade the Java program.
    """
    
    print(f"Running autograder for Java program ...")
    
    exe_command = ["java", "-cp", JAVA_JAR_PATH, JAVA_CLASS]
    grade(exe_command)

def grade_cpp():
    """
    Function to grade the C++ program.
    """
    
    print(f"Running autograder for C++ program ...")
    
    exe_command = [CPP_EXE]
    grade(exe_command)

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
