"This script generates the data files required for setting up 
an Instrument (for CDI-IRT administrations) on e-Babylab. 
Change the definitions for 'lang', 'type', and 'resp' as needed."


pacs <- c("wordbankr","plyr","dplyr","tidyr","stats4","openxlsx","mirt","mirtCAT",
          "sweep","purrr","tidyverse","tictoc","parallel","doParallel", "readr") #"tictoc","parallel","doParallel",
invisible(lapply(pacs,library,character.only=TRUE))

########## Configure settings here
lang <- "German" # use get_instruments() to see what languages and forms are available on wordbank
type <- "WS" # "WS" or "WG"
resp <- "production" # "comprehension" or "production"

d_poly <- 3
poly_mode <- "Flexi" #"Fixed" #"Fixed" # or
criteria <- "incl.anyFinite" # or "excl.Inf" — for evaluation of log = -inf
gen_list <- c("Female", "Male")

########## Functions 
# Get data from word bank
prep_data <- function(){
  admin_ws <<- get_administration_data(lang, type)
  if(lang == "English (American)"){
    admin_ws <<- admin_ws #%>% filter(norming=="TRUE")
  }
  data_ws <<- get_instrument_data(lang, type)
  if(lang == "English (American)"){
    data_ws <<- data_ws %>% filter(data_id %in% admin_ws$data_id)
  }
  items_ws <<- get_item_data(lang, type)
  
  # reduce datasets
  items_ws <<- subset(items_ws, type=="word")
  num_words <<- nrow(items_ws)
  data_ws <<- data_ws %>% filter(num_item_id %in% items_ws$num_item_id)
  if (type == "WS" | (type == "WG" & resp == "production")) {
    data_ws <- data_ws %>% 
      mutate(value = ifelse(value %in% c("produces", "yes", "sometimes", "often"),
                            1,
                            0))
  } else if (type == "WG" & resp == "comprehension") { # WG
    data_ws <- data_ws %>% 
      mutate(value = ifelse(value %in% c("no", "never", "not yet", "") | is.na(value),
                            0,
                            1))
  }
  data_ws$value <<- as.numeric(data_ws$value)
}

# Prepare admin_data_all for simulation (by merging admin_ws and data_ws)
data_in <- function(){
  if (type == "WS") {
    inner_join(data_ws, select(admin_ws, age, data_id, sex, production), by="data_id")
  } else if (type == "WG") {
    inner_join(data_ws, select(admin_ws, age, data_id, sex, all_of(resp)), by="data_id")
  }
}

# Get percentages for each word in each age
perc_word <- function(){
  temp <- select(admin_data_all,num_item_id,value,age)
  word_dist <<- temp %>% dplyr::group_by(age,num_item_id) %>% dplyr::summarise(perc = mean(value))
}

# Order percentage word
get_order <- function(df){order(df$perc)}

# Model for MLE
LL <- function(m, sd) {
  R = dnorm(scores, m, sd)
  -sum(log(R))
}

# Apply mle model
mle_model <- function(dfdata,...){
  # i <<- i + 1 # troubleshooting
  # print(i) # troubleshooting
  if (type == "WS") { # check CDI type
    scores <<- dfdata$production
    scores <<- scores[scores != 0] # remove zeros
    check <<- scores[scores != 0] 
    if (length(check) > item_threshold) {
      mle(LL, start = list(m = mean(scores), sd = sd(scores)),
          method = "L-BFGS-B")
    } else{
      NaN
    } 
  } else if (type == "WG") { # check CDI type
    if (resp == "comprehension"){
      scores <<- dfdata$comprehension
      scores <<- scores[scores != 0] # remove zeros
      check <<- scores[scores != 0] 
    } else if (resp == "production"){
      scores <<- dfdata$production
      scores <<- scores[scores != 0] # remove zeros
      check <<- scores[scores != 0]
    }
    if (length(check) > item_threshold) { 
      mle(LL, start = list(m = mean(scores), sd = sd(scores)))#, 
      # method = "L-BFGS-B")
    } else{
      NaN
    }
  }
}

# Fill in "missing" words and Reorder according to word_purr
fill_in_and_sort <- function(dfage,df){
  # ex <- data.frame(1:num_words)
  sorted <<- word_dist$num_item_id %>% unique() %>% data.frame()
  colnames(sorted) <- "num_item_id"
  full_join(sorted, df, by = "num_item_id")
}

# Configuration for polynomial
poly_cfg <- function(mode = "Flexi"){
  
  age <<- admin_data_all$age %>% unique %>% sort
  ageN <- count(admin_data_all,age)
  
  # Measures size
  if (median(as.matrix(ageN[,2])) > 200){
    size <- "large"
  } else if (median(as.matrix(ageN[,2])) <= 200 & median(as.matrix(ageN[,2])) > 100){
    size <- "medium"
  } else if (median(as.matrix(ageN[,2])) <= 100 & median(as.matrix(ageN[,2])) > 50){
    size <- "small"
  } else if (median(as.matrix(ageN[,2])) <= 50) {
    size <- "tiny"
  }
  print(size)
  
  if (mode == "Fixed"){
    matrix(3, length(age), 1, dimnames = list(c(age), c("poly")))
    
  } else if (mode == "Flexi"){
    if(type == "WS"){
      # Flexi Poly
      df_mad <- admin_data_all %>% ungroup() %>% select(age,production)
      df_mad <- aggregate(. ~ age, df_mad, function(x) c(median = median(x), mad = mad(x)))
      temp_df <- cbind(df_mad[,1],df_mad$production[,2]) %>%
        data.frame %>%
        mutate(poly = ifelse(X2 < 100, 1, 3))
      # Extract poly num only
      as.matrix(temp_df[,3])
    } else if (type == "WG" & resp == "comprehension"){
      # Flexi Poly
      df_mad <- admin_data_all %>% select(age,all_of(resp))
      df_mad <- aggregate(. ~ age, df_mad, function(x) c(median = median(x), mad = mad(x)))
      temp_df <- cbind(df_mad[,1],
                       (df_mad %>% select(all_of(resp)) %>% data.frame)[,1][,2]) %>% # dynamic columns
        data.frame %>%
        mutate(poly = ifelse(X2 < 100, 1, 3))
      # Extract poly num only
      as.matrix(temp_df[,3])
      
    } else if (type == "WG" & resp == "production"){
      
      # Flexi Poly Original
      df_mad <- admin_data_all %>% select(age,all_of(resp))
      df_mad <- aggregate(. ~ age, df_mad, function(x) c(median = median(x), mad = mad(x)))
      temp_df <- cbind(df_mad[,1],
                       (df_mad %>% select(all_of(resp)) %>% data.frame)[,1][,2]) %>% # dynamic columns
        data.frame %>%
        mutate(poly = ifelse(X2 < 100, 1, 3))
      # Extract poly num only
      as.matrix(temp_df[,3])
    }
  }
}

# Fit degree of polynomial
poly_fit_mean <- function(dfage,df,...){
  d_poly <<- idpoly[which(age == dfage)]
  if (any(is.finite(df$mean))) {
    model <<- lm(df$mean~poly(c(1:num_words), d_poly, raw = TRUE))
    pmax(20, predict(model, newdata=data.frame(c(1:num_words))))
  } else {
    NaN
  }
}

poly_fit_sd <- function(dfage,df,...){
  d_poly <<- idpoly[which(age == dfage)]
  if (any(is.finite(df$sd))) {
    model <<- lm(df$sd~poly(c(1:num_words), d_poly, raw = TRUE))
    pmax(20, predict(model, newdata=data.frame(c(1:num_words))))
  } else {
    NaN
  }
}

# log PDF of normal distribution
log_pdf <- function(df){
  log(dnorm(c(0,1:num_words),df$lm_mean,df$lm_sd), base = exp(1))
}

# Filter log dnorm pdf
filter_log_pdf <- function(df, criteria){
  if(criteria == "excl.Inf"){
    
    df$filt <- is.finite(as.numeric(map(df$log,sum)))
  } else if (criteria == "incl.anyFinite"){
    
    df$filt <- as.numeric(map(df$log,ls.is.finite))
  } else {
    cat("Input error.")
  }
}

# Filter log dnorm pdf by Rows
ls.is.finite <- function(df){
  ifelse(any(is.finite(unlist(df)))==TRUE,TRUE,FALSE)}

# sum of log (basis)
sum_log <- function(df){
  list(reduce(df,`+`) + 1)
}

# max basis
max_basis <- function(df){
  as.numeric(which(unlist(df) == max(unlist(df), na.rm = T)))
}

# max basis
max_basis_test <- function(df, value){
  if (value == 0){
    as.numeric(which(unlist(df) == max(unlist(df), na.rm = T)))
  } else if (value == 1){
    as.numeric(which(unlist(df) == max(unlist(df), na.rm = T))) + 1
  }
}

# calculate slope
get_slope <- function(df){
  diff(df)/num_words
}

# Configuration for CAT simulations
cat_cfg <- function(mode = "NoPreCAT") {
  if (mode == "NoPreCAT"){
    CAT_mode <<- list("NoPreCAT", list())
  } else if (mode == "PreCATFlex"){
    CAT_mode <<- list("PreCATFlex", list(min_items = 0, max_items = 10,
                                         criteria = "MI", method = "WLE",
                                         response_variance = TRUE))
  } else if (mode == "PreCAT") {
    CAT_mode <<- list("PreCAT", list(min_items = 10, max_items = 10,
                                     criteria = "MI", method = "WLE"))
  }
}

remove_dataID <- function(df){df %>% select(-c(data_id))}

filter_response <- function(df){Filter(var,df)}

# Fit data to IRT
fit_item_mirt <- function(df){mirt(df, 1, itemtype = "2PL", method = "EM", SE=TRUE)}

########## Code

# Prepare data
prep_data() # Extract data from wordbank
admin_ws <- admin_ws # %>% filter(!(age < 11 & production > 100)) # extra filter for extreme outliers

admin_data_all <- data_in() #  merging admin_ws and data_ws

word_dist <- perc_word() # percentage for each word in each age
word_dist$perc <- round(word_dist$perc, digits=2) # rounding

default_test <- c(num_words, 400, 200, 100, 50, 25, 10, 5)
test <- c(num_words, default_test[default_test < num_words])

# Convert admin_data_all and word_dist for purr and furr
data_purr <- admin_data_all %>% group_by(sex, value, age, num_item_id) %>%
  nest() # main set

word_purr <- word_dist %>% select(-c("num_item_id")) %>% group_by(age) %>% nest() %>%
  mutate(data = map(data, get_order))

# Modeling
#Mod# Maximum likelihood estimation
item_threshold <- 5 # min amount of data point needed to fit mle

mle_purr <- data_purr
mle_purr$model <- pmap(list(data_purr$data), mle_model)

mle_purr$mean <- foreach(i = 1:nrow(mle_purr), .combine = rbind) %do% {
  try(coef(mle_purr$model[[i]])[1], silent=TRUE) %>% as.numeric()
}
mle_purr$sd  <- foreach(i = 1:nrow(mle_purr), .combine = rbind) %do% {
  try(coef(mle_purr$model[[i]])[2], silent=TRUE) %>% as.numeric()
}

mle_purr <- mle_purr %>% select(-c("model"))
mle_purr$mean[which(is.na(mle_purr$mean))] <- NaN
mle_purr$sd[which(is.na(mle_purr$sd))] <- NaN

#Mod# poly 3 or flexi
prep_purr <- mle_purr %>% select(-c("data")) %>%
  group_by(sex,value,age) %>% nest()

prep_purr$data2 <- pmap(list(prep_purr$age,prep_purr$data), fill_in_and_sort)
prep_purr <- prep_purr %>%
  select(-c("data"))

idpoly <- poly_cfg(mode = poly_mode) # polynomial flexible, f(MAD)

poly_purr <- prep_purr
poly_purr$lm_mean <- pmap(list(prep_purr$age, prep_purr$data2), poly_fit_mean)
poly_purr$lm_sd <- pmap(list(prep_purr$age, prep_purr$data2), poly_fit_sd)
poly_purr <- poly_purr %>% unnest %>% nest(-c(sex,value,age,num_item_id))

#Mod# log PDF of normal distribution
log_pdf_purr_raw <- poly_purr
log_pdf_purr_raw$log  <- map(poly_purr$data, log_pdf)
log_pdf_purr_raw <- log_pdf_purr_raw %>%
  select(-data)

# Filter log dnorm pdf
log_pdf_purr <- log_pdf_purr_raw
log_pdf_purr$filt <- filter_log_pdf(log_pdf_purr_raw, criteria) # "excl.Inf" or
log_pdf_purr <- log_pdf_purr %>% filter(filt == 1)

#Mod# norms: basis for all items
all_basis <- log_pdf_purr %>% group_by(sex,value,age) %>% summarise(data = sum_log(log))

#Mod# Get Bmin (np_param) & slope for real-data simulation
param <- all_basis %>% group_by(sex,value,age) %>% summarise(B = max_basis(data))
np_param <- param %>% subset(value == 0)
slope <- param %>% group_by(sex,age) %>% summarise(slope = get_slope(B))

for (gen in c("Female", "Male")) {
  
  slope2 = slope %>% ungroup() %>% filter(sex == gen) %>% 
    select(age, slope) %>% spread(age, slope)
  Bmin = np_param %>% ungroup() %>% filter(sex == gen) %>% 
    select(age, B) %>% spread(age, B)
  poly_unnest <- poly_purr %>% unnest()
  
  lm_p_mean = poly_unnest %>% ungroup() %>% filter(sex == gen & value == 1) %>% 
    select(age, lm_mean, num_item_id) %>% spread(age, lm_mean) %>% 
    mutate(word_id = num_item_id) %>%
    select(-num_item_id) %>% select(word_id, colnames(.[,1:(ncol(.)-1)]))
  lm_p_sd = poly_unnest %>% ungroup() %>% filter(sex == gen & value == 1) %>% 
    select(age, lm_sd, num_item_id) %>% spread(age, lm_sd) %>% 
    mutate(word_id = num_item_id) %>%
    select(-num_item_id) %>% select(word_id, colnames(.[,1:(ncol(.)-1)]))
  lm_np_mean = poly_unnest %>% ungroup() %>% filter(sex == gen & value == 0) %>% 
    select(age, lm_mean, num_item_id) %>% spread(age, lm_mean) %>% 
    mutate(word_id = num_item_id) %>%
    select(-num_item_id) %>% select(word_id, colnames(.[,1:(ncol(.)-1)]))
  lm_np_sd = poly_unnest %>% ungroup() %>% filter(sex == gen & value == 0) %>% 
    select(age, lm_sd, num_item_id) %>% spread(age, lm_sd) %>% 
    mutate(word_id = num_item_id) %>%
    select(-num_item_id) %>% select(word_id, colnames(.[,1:(ncol(.)-1)]))
  
  if (type == "WS") {
    fname1 <- paste("p_m", gen, lang, type, sep="-")
    fname1 <- paste(fname1, "csv", sep = ".")
    fname2 <- paste("p_sd", gen, lang, type, sep="-")
    fname2 <- paste(fname2, "csv", sep = ".")
    fname3 <- paste("np_m", gen, lang, type, sep="-")
    fname3 <- paste(fname3, "csv", sep = ".")
    fname4 <- paste("np_sd", gen, lang, type, sep="-")
    fname4 <- paste(fname4, "csv", sep = ".")
    fname5 <- paste("BMin", gen, lang, type, sep="-")
    fname5 <- paste(fname5, "csv", sep = ".")
    fname6 <- paste("Slope", gen, lang, type, sep="-")
    fname6 <- paste(fname6, "csv", sep = ".")
  } else if (type == "WG") {
    fname1 <- paste("p_m", gen, lang, type, resp, sep="-")
    fname1 <- paste(fname1, "csv", sep = ".")
    fname2 <- paste("p_sd", gen, lang, type, resp, sep="-")
    fname2 <- paste(fname2, "csv", sep = ".")
    fname3 <- paste("np_m", gen, lang, type, resp, sep="-")
    fname3 <- paste(fname3, "csv", sep = ".")
    fname4 <- paste("np_sd", gen, lang, type, resp, sep="-")
    fname4 <- paste(fname4, "csv", sep = ".")
    fname5 <- paste("BMin", gen, lang, type, resp, sep="-")
    fname5 <- paste(fname5, "csv", sep = ".")
    fname6 <- paste("Slope", gen, lang, type, resp, sep="-")
    fname6 <- paste(fname6, "csv", sep = ".")
  }
  
  readr::write_csv(lm_p_mean, fname1)
  readr::write_csv(lm_p_sd, fname2)
  readr::write_csv(lm_np_mean, fname3)
  readr::write_csv(lm_np_sd, fname4)
  readr::write_csv(Bmin, fname5)
  readr::write_csv(slope2, fname6)
  
}

fname7 <- paste("word_list", lang, type, resp, sep="-")
fname7 <- paste(fname7, "csv", sep = ".")
wordonly <- items_ws %>% mutate(word = definition, word_id = num_item_id) %>%
  select(word_id, word)
readr::write_csv(wordonly, fname7)

#### Item Response Theory, IRT
cat_cfg(mode = "NoPreCAT") # NoPreCAT

num_words <- max(admin_data_all$num_item_id)
test <- c(num_words, 400, 200, 100, 50, 25, 10, 5)

# Fit IRT (overall)
data_irt <- admin_data_all %>% #filter(between(age, 16, 30)) %>%
  select(value,num_item_id,data_id) %>%
  spread(num_item_id,value) %>% select(-data_id)
data_irt <- Filter(var,data_irt)
items <- mirt(data_irt, 1, itemtype = "2PL", method = "EM", SE=TRUE)

# Extract parameters only (a1, d, g, u)
for (i in 1:(length(items@ParObjects$pars) - 1)){
  print(i)
  if (i == 1) {
    irtparam <- coef(items)[[i]][1,1:4] 
  } else {
    irtparam <- rbind(irtparam, coef(items)[[i]][1,1:4]) 
  }
}
rownames(irtparam) <- 1:nrow(irtparam)

IRT_Parameters <- irtparam %>% data.frame() %>% 
  mutate(word_id = colnames(data_irt) %>% as.numeric()) %>% 
  select(word_id, colnames(.[,2:(ncol(.)-1)]))

if (type == "WG") {
  fname8 <- paste("IRT_Parameters", lang, type, resp, sep="-")
  fname8 <- paste(fname8, "csv", sep = ".")
} else if (type == "WS") {
  fname8 <- paste("IRT_Parameters", lang, type, sep="-")
  fname8 <- paste(fname8, "csv", sep = ".")
}

readr::write_csv(IRT_Parameters, fname8)
### END of Modeling ###

