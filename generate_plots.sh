# only plot enumeration results



SCRIPT="python examples/plot_enumeration_results.py -s"


function generate(){
    $SCRIPT $1 enumeration/results_nonterminals_detailed.csv time_wrt_programs
    mv fig.png detailed_nonterminals${2}.png 
    $SCRIPT $1 enumeration/results_nonterminals_growth.csv time_wrt_non_terminals
    mv fig.png growth_nonterminals${2}.png 
    $SCRIPT $1 enumeration/results_distance_detailed.csv time_wrt_programs
    mv fig.png detailed_distance${2}.png 
    $SCRIPT $1 enumeration/results_distance_growth.csv time_wrt_non_terminals
    mv fig.png growth_distance${2}.png 
    $SCRIPT $1 enumeration/results_derivations_detailed.csv time_wrt_programs
    mv fig.png detailed_derivation_rules${2}.png 
    $SCRIPT $1 enumeration/results_derivations_growth.csv time_wrt_rules
    mv fig.png growth_derivation_rules${2}.png
}

generate "-l" ""
generate "" "_nolegend"