<!-- PAGE 1 START -->
Page: 1/11
SAMPLE QUESTION PAPER (THEORY)
CLASS: XII SESSION: 2024-25
COMPUTER SCIENCE (083)
Time allowed: 3 Hours
Maximum Marks: 70
General Instructions:
● This question paper contains 37 questions.
● All questions are compulsory. However, internal choices have been provided in some
questions. Attempt only one of the choices in such questions
● The paper is divided into 5 Sections- A, B, C, D and E.
● Section A consists of 21 questions (1 to 21). Each question carries 1 Mark.
● Section B consists of 7 questions (22 to 28). Each question carries 2 Marks.
● Section C consists of 3 questions (29 to 31). Each question carries 3 Marks.
● Section D consists of 4 questions (32 to 35). Each question carries 4 Marks.
● Section E consists of 2 questions (36 to 37). Each question carries 5 Marks.
● All programming questions are to be answered using Python Language only.
● In case of MCQ, text of the correct answer should also be written.
Q No.
Section-A (21 x 1 = 21 Marks)
Marks

## 1.
State True or False:
The Python interpreter handles logical errors during code execution.
(1)

## 2.
Identify the output of the following code snippet:
text = "PYTHONPROGRAM"
text=text.replace('PY','#')
print(text)
(A) #THONPROGRAM
(B) ##THON#ROGRAM
(C) #THON#ROGRAM
(D) #YTHON#ROGRAM
(1)

## 3.
Which of the following expressions evaluates to False?
(A) not(True) and False
(B) True or False
(C) not(False and True)
(D) True and not(False)
(1)

## 4.
What is the output of the expression?
country='International'
print(country.split("n"))
(A) ('I', 'ter', 'atio', 'al')
(B) ['I', 'ter', 'atio', 'al']
(C) ['I', 'n', 'ter', 'n', 'atio', 'n', 'al']
(D) Error
(1)
<!-- PAGE 1 END -->

<!-- PAGE 2 START -->
Page: 2/11

## 5.
What will be the output of the following code snippet?
message= "World Peace"
print(message[-2::-2])
(1)

## 6.
What will be the output of the following code?
tuple1 = (1, 2, 3)
tuple2 = tuple1
tuple1 += (4,)
print(tuple1 == tuple2)
(A) True
(B) False
(C) tuple1
(D) Error
(1)

## 7.
If my_dict is a dictionary as defined below, then which of the following
statements will raise an exception?
my_dict = {'apple': 10, 'banana': 20, 'orange': 30}
(A) my_dict.get('orange')
(B) print(my_dict['apple', 'banana'])
(C) my_dict['apple']=20
(D) print(str(my_dict))
(1)

## 8.
What does the list.remove(x) method do in Python?
(A) Removes the element at index x from the list
(B) Removes the first occurrence of value x from the list
(C) Removes all occurrences of value x from the list
(D) Removes the last occurrence of value x from the list
(1)

## 9.
If a table which has one Primary key and two alternate keys. How many
Candidate keys will this table have?
(A) 1
(B) 2
(C) 3
(D) 4
(1)

## 10.
Write the missing statement to complete the following code:
file = open("example.txt", "r")
data = file.read(100)
____________________ #Move the file pointer to the
beginning of the file
next_data = file.read(50)
file.close()
(1)

## 11.
State whether the following statement is True or False:
The finally block in Python is executed only if no exception occurs
in the try block.
(1)
<!-- PAGE 2 END -->

<!-- PAGE 3 START -->
Page: 3/11

## 12.
What will be the output of the following code?
c = 10
def add():
global c
c = c + 2
print(c,end='#')
add()
c=15
print(c,end='%')
(A) 12%15#
(B) 15#12%
(C) 12#15%
(D) 12%15#
(1)

## 13.
Which SQL command can change the degree of an existing relation?
(1)

## 14.
What will be the output of the query?
SELECT * FROM products WHERE product_name LIKE
'App%';
(A) Details of all products whose names start with 'App'
(B) Details of all products whose names end with 'App'
(C) Names of all products whose names start with 'App'
(D) Names of all products whose names end with 'App'
(1)

## 15.
In which datatype the value stored is padded with spaces to fit the specified
length.
(A) DATE
(B) VARCHAR
(C) FLOAT
(D) CHAR
(1)

## 16.
Which aggregate function can be used to find the cardinality of a table?
(A) sum()
(B) count()
(C) avg()
(D) max()
(1)

## 17.
Which protocol is used to transfer files over the Internet?
(A) HTTP
(B) FTP
(C) PPP
(D) HTTPS
(1)
<!-- PAGE 3 END -->

<!-- PAGE 4 START -->
Page: 4/11

## 18.
Which network device is used to connect two networks that use different
protocols?
(A) Modem
(B) Gateway
(C) Switch
(D) Repeater
(1)

## 19.
Which switching technique breaks data into smaller packets for
transmission, allowing multiple packets to share the same network
resources.
(1)

## Q20 and Q21 are Assertion(A) and Reason(R) based questions. Mark
the correct choice as:
(A) Both A and R are true and R is the correct explanation for A
(B) Both A and R are true and R is not the correct explanation
for A
(C) A is True but R is False
(D) A is False but R is True

## 20.
Assertion (A): Positional arguments in Python functions must be passed in
the exact order in which they are defined in the function
signature.
Reasoning (R): This is because Python functions automatically assign
default values to positional arguments.
(1)

## 21.
Assertion (A): A SELECT command in SQL can have both WHERE and
HAVING clauses.
Reasoning (R): WHERE and HAVING clauses are used to check
conditions, therefore, these can be used interchangeably.
(1)
Q No
Section-B ( 7 x 2=14 Marks)
Marks

## 22.
How is a mutable object different from an immutable object in Python?
Identify one mutable object and one immutable object from the following:
(1,2), [1,2], {1:1,2:2}, ‘123’
(2)

## 23.
Give two examples of each of the following:
(I) Arithmetic operators   (II) Relational operators
(2)

## 24.
If  L1=[1,2,3,2,1,2,4,2, . . . ],  and L2=[10,20,30, . . .], then
(Answer using builtin functions only)
(I)
A) Write a statement to count the occurrences of 4 in L1.
OR
B) Write a statement to sort the elements of list L1 in ascending
order.
(2)
<!-- PAGE 4 END -->

<!-- PAGE 5 START -->
Page: 5/11
(II)
A) Write a statement to insert all the elements of L2 at the end of L1.
OR
B) Write a statement to reverse the elements of list L2.

## 25.
Identify the correct output(s) of the following code. Also write the minimum
and the maximum possible values of the variable b.
import random
a="Wisdom"
b=random.randint(1,6)
for i in range(0,b,2):
print(a[i],end='#')
(A) W#
(B) W#i#
(C) W#s#
(D) W#i#s#
(2)

## 26.
The code provided below is intended to swap the first and last elements of
a given tuple. However, there are syntax and logical errors in the code.
Rewrite it after removing all errors. Underline all the corrections made.
def swap_first_last(tup)
if len(tup) < 2:
return tup
new_tup = (tup[-1],) + tup[1:-1] + (tup[0])
return new_tup
result = swap_first_last((1, 2, 3, 4))
print("Swapped tuple: "  result)
(2)

## 27.
(I)
A) What constraint should be applied on a table column so that
duplicate values are not allowed in that column, but NULL is
allowed.
OR
B) What constraint should be applied on a table column so that
NULL is not allowed in that column, but duplicate values are
allowed.
(2)
<!-- PAGE 5 END -->

<!-- PAGE 6 START -->
Page: 6/11
(II)
A) Write an SQL command to remove the Primary Key constraint
from a table, named MOBILE. M_ID is the primary key of the
table.
OR
B) Write an SQL command to make the column M_ID  the Primary
Key of an already existing table, named MOBILE.

## 28.
A) List one advantage and one disadvantage of star topology.
OR
B) Expand the term SMTP. What is the use of SMTP?
(2)
Q No.
Section-C ( 3 x 3 = 9 Marks)
Marks

## 29.
A) Write a Python function that displays all the words containing @cmail
from a text file "Emails.txt".
OR
B) Write a Python function that finds and displays all the words longer than
5 characters from a text file "Words.txt".
(3)

## 30.
A) You have a stack named BooksStack that contains records of books.
Each book record is represented as a list containing book_title,
author_name, and publication_year.
Write the following user-defined functions in Python to perform the
specified operations on the stack BooksStack:
(I) push_book(BooksStack, new_book): This function takes the stack
BooksStack and a new book record new_book as arguments and
pushes the new book record onto the stack.
(II) pop_book(BooksStack): This function pops the topmost book record
from the stack and returns it. If the stack is already empty, the
function should display "Underflow".
(III) peep(BookStack): This function displays the topmost element of
the stack without deleting it. If the stack is empty, the function
should display 'None'.
OR
(B) Write the definition of a user-defined function `push_even(N)` which
accepts a list of integers in a parameter `N` and pushes all those integers
which are even from the list `N` into a Stack named `EvenNumbers`.
Write function pop_even() to pop the topmost number from the stack and
returns it. If the stack is already empty, the function should display "Empty".
Write function Disp_even() to display all element of the stack without
deleting them. If the stack is empty, the function should display 'None'.
(3)
<!-- PAGE 6 END -->

<!-- PAGE 7 START -->
Page: 7/11
For example:
If the integers input into the list `VALUES` are:
[10, 5, 8, 3, 12]
Then the stack `EvenNumbers` should store:
[10, 8, 12]

## 31.
Predict the output of the following code:
d = {"apple": 15, "banana": 7, "cherry": 9}
str1 = ""
for key in d:
str1 = str1 + str(d[key]) + "@" + “\n”
str2 = str1[:-1]
print(str2)
OR
Predict the output of the following code:
line=[4,9,12,6,20]
for I in line:
for j in range(1,I%5):
print(j,’#’,end=””)
print()
(3)
Q No.
Section-D ( 4 x 4 = 16 Marks)
Marks

## 32.
Consider the table ORDERS as given below
O_Id
C_Name
Product
Quantity
Price
1001
Jitendra
Laptop
1
12000
1002
Mustafa
Smartphone
2
10000
1003
Dhwani
Headphone
1
1500
Note: The table contains many more records than shown here.
A) Write the following queries:
(I)
To display the total Quantity for each Product, excluding
Products with total Quantity less than 5.
(II)
To display the orders table sorted by total price in descending
order.
(III)
To display the distinct customer names from the Orders table.
(4)
<!-- PAGE 7 END -->

<!-- PAGE 8 START -->
Page: 8/11
(IV)
Display the sum of Price of all the orders for which the quantity
is null.
OR
B) Write the output
(I) Select c_name, sum(quantity) as total_quantity
from orders group by c_name;
(II) Select * from orders where product like
'%phone%';
(III) Select o_id, c_name, product, quantity, price
from orders where price between 1500 and 12000;
(IV) Select max(price) from orders;

## 33.
A csv file "Happiness.csv" contains the data of a survey. Each record of the
file contains the following data:
● Name of a country
● Population of the country
● Sample Size (Number of persons who participated in the survey in
that country)
● Happy (Number of persons who accepted that they were Happy)
For example, a sample record of the file may be:
[‘Signiland’, 5673000, 5000, 3426]
Write the following Python functions to perform the specified operations on
this file:
(I)
Read all the data from the file in the form of a list and display all
those records for which the population is more than 5000000.
(II)
Count the number of records in the file.
(4)

## 34.
Saman has been entrusted with the management of Law University
Database. He needs to access some information from FACULTY and
COURSES tables for a survey analysis. Help him extract the following
information by writing the desired SQL queries as mentioned below.
Table: FACULTY
F_ID
FName
LName
Hire_Date
Salary
102
Amit
Mishra
12-10-1998
12000
103
Nitin
Vyas
24-12-1994
8000
104
Rakshit
Soni
18-5-2001
14000
105
Rashmi
Malhotra
11-9-2004
11000
106
Sulekha
Srivastava
5-6-2006
10000
Table: COURSES
C_ID
F_ID
CName
Fees
C21
102
Grid Computing
40000
C22
106
System Design
16000
(4)
<!-- PAGE 8 END -->

<!-- PAGE 9 START -->
Page: 9/11
C23
104
Computer Security
8000
C24
106
Human Biology
15000
C25
102
Computer Network
20000
C26
105
Visual Basic
6000
(I) To display complete details (from both the tables) of those Faculties
whose salary is less than 12000.
(II) To display the details of courses whose fees is in the range of 20000
to 50000 (both values included).
(III) To increase the fees of all courses by 500 which have "Computer"
in their Course names.
(IV) (A) To display names (FName and LName) of faculty taking System
Design.
OR
(B) To display the Cartesian Product of these two tables.

## 35.
A table, named STATIONERY, in ITEMDB database, has the following
structure:
Field
Type
itemNo
int(11)
itemName
varchar(15)
price
float
qty
int(11)
Write the following Python function to perform the specified operation:
AddAndDisplay(): To input details of an item and store it in the table
STATIONERY. The function should then retrieve and display all records
from the STATIONERY table where the Price is greater than 120.
Assume the following for Python-Database connectivity:
Host: localhost,    User: root,    Password: Pencil
(4)
Q.No.

# SECTION E (2 X 5 = 10 Marks)

Marks

## 36.
Surya is a manager working in a recruitment agency. He needs to manage
the records of various candidates. For this, he wants the following
information of each candidate to be stored:
- Candidate_ID – integer
- Candidate_Name – string
- Designation – string
- Experience – float
You, as a programmer of the company, have been assigned to do this job
for Surya.
(I) Write a function to input the data of a candidate and append it in a
binary file.
(5)
<!-- PAGE 9 END -->

<!-- PAGE 10 START -->
Page: 10/11
(II) Write a function to update the data of candidates whose experience
is more than 10 years and change their designation to "Senior
Manager".
(III) Write a function to read the data from the binary file and display the
data of all those candidates who are not "Senior Manager".

## 37.
Event Horizon Enterprises is an event planning organization. It is planning
to set up its India campus in Mumbai with its head office in Delhi. The
Mumbai campus will have four blocks/buildings - ADMIN, FOOD, MEDIA,
DECORATORS. You, as a network expert, need to suggest the best
network-related solutions for them to resolve the issues/problems
mentioned in points (I) to (V), keeping in mind the distances between
various blocks/buildings and other given parameters.
Block to Block distances (in Mtrs.)
From
To
Distance
ADMIN
FOOD
42 m
ADMIN
MEDIA
96 m
ADMIN
DECORATORS
48 m
FOOD
MEDIA
58 m
FOOD
DECORATORS
46 m
MEDIA
DECORATORS
42 m
Distance of Delhi Head Office from Mumbai Campus = 1500 km
Number of computers in each of the blocks/Center is as follows:
ADMIN
30
FOOD
18
MEDIA
25
DECORATORS
20
DELHI HEAD
OFFICE
18
(5)
<!-- PAGE 10 END -->

<!-- PAGE 11 START -->
Page: 11/11
(I)
Suggest the most appropriate location of the server inside the
MUMBAI campus. Justify your choice.
(II)
Which hardware device will you suggest to connect all the
computers within each building?
(III)
Draw the cable layout to efficiently connect various buildings
within the MUMBAI campus. Which cable would you suggest for
the most efficient data transfer over the network?
(IV)
Is there a requirement of a repeater in the given cable layout?
Why/ Why not?
(V)
A) What would be your recommendation for enabling live visual
communication between the Admin Office at the Mumbai campus
and the DELHI Head Office from the following options:
a) Video Conferencing
b) Email
c) Telephony
d) Instant Messaging
OR
B) What type of network (PAN, LAN, MAN, or WAN) will be set up
among the computers connected in  the MUMBAI campus?
<!-- PAGE 11 END -->