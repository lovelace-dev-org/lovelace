sed -r 's/"([^\/]+\/[^\/]+\/)[EL].*/\1/' cp-params | sort | uniq | wc -l
