; Hacker's delight 13, difficulty 5
; sign function

(set-logic BV)

(define-fun hd13 ((x (BitVec 64))) (BitVec 64) (ite (bvsle x #x0000000000000000) (ite (= var0 #x0000000000000000) #x0000000000000000 (bvneg #x0000000000000001)) #x0000000000000001))

(synth-fun f ((x (BitVec 64))) (BitVec 64)
    ((Start (BitVec 64) (
		(bvnot Start)
						 (bvxor Start Start)
						 (bvand Start Start)
						 (bvor Start Start)
						 (bvneg Start)
						 (bvadd Start Start)
						 (bvmul Start Start)
						 (bvudiv Start Start)
						 (bvurem Start Start)
						 (bvlshr Start Start)
						 (bvashr Start Start)
						 (bvshl Start Start)
						 (bvsdiv Start Start)
						 (bvsrem Start Start)
						 (bvsub Start Start)
                         x
						 #x000000000000001f
						 #x0000000000000001
						 #x0000000000000000
						 #xffffffffffffffff
						 (ite StartBool Start Start)
						 ))

                         (StartBool Bool(
							 (= Start Start)
                         ))))

(declare-var x (BitVec 64))
(constraint (= (hd13 x) (f x)))
(check-synth)
