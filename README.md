# CL3-rota
We use this for constructing the swab-inactivation rota.

Use Python 3
```
pip install ortools
git clone https://github.com/theosanderson/CL3-rota.git
cd CL3-rota
python rota.py > output.tsv
```

The script will run for 60 seconds - you can adjust the time limit in the script to allow a more optimal solution.

## What the script does

The script imposes a number of hard constraints:
 - 9 people must be assigned for each main shift, 3 must be assigned for each standby shift
 - no-one can work when their availability is listed as No
 - no-one can work twice on the same day
 - no-one can be assigned more shifts than they are listed as willing to do
 
 When there are multiple solutions that satisfy these constrains it seeks to minimise a number of "bad things":
 - people working when their availability is only listed as "Maybe"
 - people not working when their availability is listed as "Best"
 - the overall variance in terms of the score for the amount of work people do (score = 3 * number_of_main_shifts + 2 * number_of_standby_shifts)
