import logging
from ortools.sat.python import cp_model
import pandas
data = pandas.read_csv("rota.csv")

days = ["Mon", "Tue", "Wed", "Thur", "Fri", "Sat", "Sun"]
times = ["am", "pm"]
num_main_workers = 9
num_standby_workers = 3

# how much worse main shifts are than standby shifts. Must be an integer.
main_shift_weighting = 3
# how much worse main shifts are than standby shifts. Must be an integer.
standby_shift_weighting = 2
best_weighting = -1


max_time = 900  # max time to look for solutions in seconds
debug_info = True  # Set to True and the rota will record Yes/Maybe requests

days_index = range(len(days))
people_index = list(data['First'].index)
times_index = range(len(times))
model = cp_model.CpModel()
main_shifts = {}
standby_shifts = {}

total_num_shift_costs = len(days_index)*len(times_index) * (num_main_workers*main_shift_weighting + num_standby_workers*standby_shift_weighting)
total_people = len(people_index)
average_num_shift_costs=  int(total_num_shift_costs/total_people)


total_num_main_shift_costs = len(days_index)*len(times_index) * (num_main_workers*main_shift_weighting )

average_num_main_shift_costs=  int(total_num_main_shift_costs/total_people)

def get_variance_component(to_sum, average):
    a = model.NewIntVar(-250, 250, '')
    model.Add(a ==sum(to_sum)  - average)


  

    e = model.NewIntVar(0, 250, '')
    model.AddAbsEquality(e,a)


    square_x = model.NewIntVar(0, 250, "")
    model.AddProdEquality(square_x, [e, e])
    return square_x
# Here we create True/False for every person,day,shift possibility for main and standby shifts:
for p in people_index:
    for d in days_index:
         for t in times_index:
                main_shifts[(p, d,
                             t)] = model.NewBoolVar('shift_n%id%is%i' % (p, d, t))
                standby_shifts[(p, d,
                                t)] = model.NewBoolVar('standby_shift_n%id%is%i' % (p, d, t))

# Here we state that there must be X main workers and Y standby workers per shift
for d in days_index:
      for t in times_index:
            model.Add(sum(main_shifts[(p, d, t)]
                          for p in people_index) == num_main_workers)
            model.Add(sum(standby_shifts[(p, d, t)]
                          for p in people_index) == num_standby_workers)

# Here we state that one person can be assigned no more than one shift per day
for p in people_index:
        for d in days_index:
            model.Add(
                sum(main_shifts[(p, d, t)] + standby_shifts[(p, d, t)] for t in times_index) <= 1)

# Here we state that people cannot work more days than they have offered to:
people_num_shifts_list = []
people_num_main_shifts_list = []
for p in people_index:
  try:
    max_shifts = int(data['days'][p])
  except ValueError:
    # if they have not entered a numeric value assume they are prepared to work five days
    max_shifts = 5
  to_sum = []
  to_sum_main = []
  to_sum_raw = []
  for d in days_index:
    for t in times_index:
      to_sum.append(main_shift_weighting *
                    main_shifts[(p, d, t)] + standby_shift_weighting*standby_shifts[(p, d, t)])
      to_sum_main.append(main_shift_weighting *main_shifts[(p, d, t)])
      to_sum_raw.append(main_shifts[(p, d, t)] + standby_shifts[(p, d, t)])
  # People cannot work more than offered
  model.Add(sum(to_sum_raw) <= max_shifts)

  # We define a variable to hold the number of shifts this person is doing so we can then find the maximum of all of these


  square_x = get_variance_component(to_sum, average_num_shift_costs)
  people_num_shifts_list.append(square_x)

  square_x = get_variance_component(to_sum_main, average_num_main_shift_costs)
  people_num_main_shifts_list.append(square_x)

# We force this new variable to be the maximum shifts one person does (with weightings)


# Here we work out how much people have to work on days they are only "Maybe" willing to work on
# we can then minimise this

loss_list = []
for p in people_index:
  for d in days_index:
    for t in times_index:
      entry = data[days[d]+"_"+times[t]][p]
      try:
        entry = entry.lower().strip()
      except AttributeError:
        entry = "no"
        logging.warning(f"'{entry}'' parsed as no.\n\n")
      if entry == "yes":
        pass
      elif entry == "best":
        loss_list.append(main_shifts[(p, d, t)] * main_shift_weighting*best_weighting)

      elif entry == "maybe":
        # If maybe we count how many times we had to use maybes to try to minimise
        loss_list.append(main_shifts[(p, d, t)] * main_shift_weighting)
        loss_list.append(standby_shifts[(p, d, t)] * standby_shift_weighting)
      else:
        # If no we add a hard constraint
        model.Add(main_shifts[(p, d, t)] == 0)
        model.Add(standby_shifts[(p, d, t)] == 0)

model.Minimize(10*sum(loss_list) + sum(people_num_shifts_list) )


solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = max_time
result = solver.Solve(model)

print(result)
# Statistics.
#print()
#print('Statistics')
#print('  - conflicts       : %i' % solver.NumConflicts())
#print('  - branches        : %i' % solver.NumBranches())
#print('  - wall time       : %f s' % solver.WallTime())
print('  - objective: %f' % solver.ObjectiveValue() )


# The solver has now solved the problem
# The rest of the code is just to print out the outputs

main_counts = [0 for x in people_index]
standby_counts = [0 for x in people_index]
maybe_counts = [0 for x in people_index]
shift_strings = [ [] for x in people_index]

main_output = {}
standby_output = {}

for d in days_index:
    for t in times_index:
      main_output[(d, t)] = []
      standby_output[(d, t)] = []
      for p in people_index:

          if solver.Value(main_shifts[(p, d, t)]) == 1:
                shift_strings[p].append(  days[d]+" "+times[t] + " (main)")
                main_counts[p] = main_counts[p]+1
                if debug_info:
                  main_output[(d, t)].append(data['First'][p] +
                                             "_" + data[days[d]+"_"+times[t]][p])
                else:
                  main_output[(d, t)].append(data['First'][p])
                if data[days[d]+"_"+times[t]][p] == "maybe":
                  maybe_counts[p] = maybe_counts[p]+1




          elif solver.Value(standby_shifts[(p, d, t)]) == 1:
                shift_strings[p].append(days[d]+" "+times[t] + " (standby)")
                standby_counts[p] = standby_counts[p]+1
                if debug_info:
                  standby_output[(d, t)].append(
                      data['First'][p] + "_" + data[days[d]+"_"+times[t]][p])
                else:
                  standby_output[(d, t)].append(data['First'][p])

                if data[days[d]+"_"+times[t]][p] == "maybe":
                  maybe_counts[p] = maybe_counts[p]+1

line = ""
for d in days_index:
  for t in times_index:
    line = line + days[d]+"_"+times[t]+"\t"
print(line)

for r in range(num_main_workers+num_standby_workers):
  if r == num_main_workers:  # blank line between main and standby
    print("".join(["\t" for x in range(d*t)]))
  line = ""
  for d in days_index:
    for t in times_index:
      if r < num_main_workers:
        name = main_output[(d, t)][r]
      else:
        name = standby_output[(d, t)][r-num_main_workers]
      line = line + name + "\t"
  print(line)

print()
print()
print("TOTALS")
print()
print("Name\tMain shifts\tStandby shifts\tMaybe shifts \t Scoring \t Max shifts willing to do")
for p in people_index:
  try:
    max_days = str(int(data['days'][p]))
  except:
    max_days = "Inf"
  print(data['First'][p] + " " + data['Last'][p] + "\t" +
        str(main_counts[p])+"\t" + str(standby_counts[p])+"\t" + str(maybe_counts[p])+"\t" + str(standby_counts[p]*standby_shift_weighting + main_counts[p]*main_shift_weighting) + "\t" + max_days)


for p in people_index:
  if main_counts[p]>0 or standby_counts[p]>0:
    print(data['email'][p] +"\t"+data['First'][p] +"\t"+ ",".join(shift_strings[p] ))        
