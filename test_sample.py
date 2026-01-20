#!/usr/bin/env python3
"""
This file contains intentional code quality issues for testing.
"""

import pickle
import os
import sqlite3


def process_user_data(user_input):
    """Dangerous function with security issues."""
    # SQL Injection vulnerability
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE name = '{user_input}'"  # SQL Injection!
    cursor.execute(query)
    
    # Using eval with user input - CRITICAL SECURITY ISSUE
    result = eval(user_input)  # Dangerous!
    
    # Pickle deserialization vulnerability
    with open('data.pkl', 'rb') as f:
        data = pickle.load(f)  # Security risk!
    
    return result


def complex_nested_function(data):
    """Function with excessive nesting and high complexity."""
    result = []
    for i in range(10):
        if i > 0:
            if i % 2 == 0:
                if i != 5:
                    for j in range(5):
                        if j > 2:
                            if j != 4:
                                result.append(i * j)
                                if len(result) > 100:
                                    if result[-1] > 50:
                                        result.pop()
                                    else:
                                        if result:
                                            pass
    return result


def very_long_function_that_does_many_things():
    """This function is way too long and should be refactored."""
    # Lines 45-80: Variable assignments
    var1 = 1
    var2 = 2
    var3 = 3
    var4 = 4
    var5 = 5
    var6 = 6
    var7 = 7
    var8 = 8
    var9 = 9
    var10 = 10
    var11 = 11
    var12 = 12
    var13 = 13
    var14 = 14
    var15 = 15
    
    # Lines 62-75: Processing logic
    temp1 = var1 + var2
    temp2 = var2 + var3
    temp3 = var3 + var4
    temp4 = var4 + var5
    temp5 = var5 + var6
    temp6 = var6 + var7
    temp7 = var7 + var8
    temp8 = var8 + var9
    temp9 = var9 + var10
    temp10 = var10 + var11
    temp11 = var11 + var12
    temp12 = var12 + var13
    temp13 = var13 + var14
    temp14 = var14 + var15
    
    # Lines 76-85: More processing
    final1 = temp1 * temp2
    final2 = temp2 * temp3
    final3 = temp3 * temp4
    final4 = temp4 * temp5
    final5 = temp5 * temp6
    final6 = temp6 * temp7
    final7 = temp7 * temp8
    final8 = temp8 * temp9
    
    # Lines 86-95: Return logic
    result_a = final1 + final2
    result_b = final2 + final3
    result_c = final3 + final4
    result_d = final4 + final5
    result_e = final5 + final6
    result_f = final6 + final7
    result_g = final7 + final8
    
    return [result_a, result_b, result_c, result_d, result_e, result_f, result_g]


def another_function_with_issues(x, y, z):
    """Another function with nested conditions."""
    if x > 0:
        if y > 0:
            if z > 0:
                if x + y + z > 10:
                    return x * y * z
                else:
                    if x > 5:
                        if y > 3:
                            return x + y + z
    return 0


def unused_function():
    """This function is never called."""
    print("This should be removed")
    return "dead code"


def main():
    """Main function to test the module."""
    # Unused variable
    unused_var = 42
    
    # Process some data
    data = process_user_data("test_user")
    
    # Call the long function
    results = very_long_function_that_does_many_things()
    
    # Call nested function
    nested = complex_nested_function([1, 2, 3])
    
    # Another call
    another_function_with_issues(1, 2, 3)
    
    return data


if __name__ == "__main__":
    main()
