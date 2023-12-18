#!/usr/bin/bash
# ============================================================
# PARAMETERS ==================================================
# ============================================================
DSL="deepcoder"
TEST_FILENAME="test_deepcoder"
TEST_FILE="./$DSL/$TEST_FILENAME.pickle"
ALL_SEEDS="1" 
SEARCH="bee_search"
# ALL_SEEDS="1" 
# ============================================================
# FLAGS =======================================================
# ============================================================
MODEL_FLAGS="--b 16"
GEN_TAGS="--inputs 2 --programs 1000"
TRAIN_TAGS="$MODEL_FLAGS -e 2"
EVAL_TAGS="-t 700000"
# ============================================================
# CODE =======================================================
# ============================================================
function abort_on_failure(){
    out=$?
    if [ $out != 0 ]; then
        echo "An error has occured"
        exit 1
    fi
}
function gen_data(){
    dsl=$1
    seed=$2
    train_file=./$DSL/train_${dsl}_seed_${seed}.pickle
    if [ ! -f "$train_file" ]; then
        python examples/pbe/dataset_generator_unique.py --dsl $dsl --dataset $dsl.pickle -o $train_file --seed $seed $GEN_TAGS
        abort_on_failure
    fi
}

function do_exp(){
    dsl=$1
    seed=$2
    train_file=./$DSL/train_${dsl}_seed_${seed}.pickle
    model_name=seed_${seed}_
    model_file="./$DSL/$model_name.pt"
    if [ ! -f "$model_file" ]; then
        python examples/pbe/model_trainer.py --dsl $dsl --dataset $train_file --seed $seed -o $model_file $TRAIN_TAGS
        abort_on_failure
    fi

    python examples/pbe/model_prediction.py --dsl $dsl --dataset $TEST_FILE --model $model_file --support $train_file ${MODEL_FLAGS}
    abort_on_failure
    pcfg_file="./$DSL/pcfgs_${TEST_FILENAME}_$model_name.pickle"
    for solver in $SEARCH
    do
        python examples/pbe/compare_enumeration.py --dsl $dsl --dataset $TEST_FILE -o "./$dsl" --support $train_file --pcfg $pcfg_file --search $solver ${EVAL_TAGS} &
        abort_on_failure
    done
    wait
} 

# Make folder
if [ ! -d "./$DSL" ]; then
    mkdir "./$DSL"
fi
# Generate test dataset
if [ ! -f "$TEST_FILE" ]; then
    python examples/pbe/dataset_generator_unique.py --dsl $DSL --dataset $DSL.pickle -o $TEST_FILE --seed 2410 --inputs 2 --programs 100
    abort_on_failure
fi
# Generate train datasets
for my_seed in $ALL_SEEDS
do 
    gen_data $DSL $my_seed
    do_exp $DSL $my_seed ""
done