pacman::p_load(rvest,dplyr,xml2,tidyverse,RCurl,XML,xlsx)
pacman::p_load(rvest,dplyr,xml2,tidyverse,RCurl,XML,readxl,splitstackshape,writexl)

pages <- 193

for (i in 1:pages){
  txt1 <- paste("url <- 'https://www.gov.pl/web/dyplomacja/aktualnosci?page=",i,"&size=10'",sep="")
  eval(parse(text=txt1))
  web_lp <- read_html(url)
  titles <- web_lp %>% html_nodes(".title") %>% html_text()
  titles <- str_squish(titles)
  dates <- web_lp %>% html_nodes(".event") %>% html_text()
  dates <- str_squish(dates)
  urls <- web_lp %>% html_nodes("article") %>% html_nodes("a") %>% html_attr("href")
  urls <- urls[1:length(titles)]
  urls <- paste0('https://www.gov.pl',urls)
  df_temp <- data.frame(url=urls,title=titles,date=dates)
  df_temp$text <- NA
  
  for (j in 1:dim(df_temp)[1]){
    text <- read_html(df_temp$url[j]) %>% html_nodes("#main-content") %>% html_text()
    text <- str_squish(text)
    df_temp$text[j] <- text
    ### Acá correr el código de traducir.
    getParam = df_temp$title[j]
    translateFrom = "auto"
    translateTo = "en"
    search <- URLencode(getParam)
    URL_title <- paste("https://translate.google.pl/m?hl=",translateFrom,"&sl=",translateFrom,"&tl=",translateTo,"&ie=UTF-8&prev=_m&q=",search,sep="")
    page <- read_html(URL_title)
    body_title <- html_node(page,'.result-container') %>% html_text()
    if (nchar(df_temp$text[j], type = "chars", allowNA = FALSE, keepNA = NA)>2500){
      sentences <- unlist(strsplit(df_temp$text[j], "\\. ", perl=T))
      num_sentences <- length(sentences)
      body_text22 <- ""
      for (n in 1:num_sentences){
        getParam3 <- sentences[n]
        search3 <- URLencode(getParam3)
        URL_btext <- paste("https://translate.google.com/m?hl=",translateFrom,"&sl=",translateFrom,"&tl=",translateTo,"&ie=UTF-8&prev=_m&q=",search3,sep="")
        page3 <- read_html(URL_btext)
        body_text22 <- paste(body_text22, html_node(page3,'.result-container') %>% html_text(), sep=". ")
      }
    } else {
      getParam3 <- df_temp$text[j]
      search3 <- URLencode(getParam3)
      URL_btext <- paste("https://translate.google.com/m?hl=",translateFrom,"&sl=",translateFrom,"&tl=",translateTo,"&ie=UTF-8&prev=_m&q=",search3,sep="")
      page3 <- read_html(URL_btext)
      body_text22 <- html_node(page3,'.result-container') %>% html_text()
    }
    df_temp$title[j] <- body_title
    df_temp$text[j] <- body_text22
    print(df_temp$date[j])
  }
  if (i==1){
    df_final <- df_temp
  } else {
    df_final <- rbind(df_final,df_temp)
  }
}

saveRDS(df_final, file = "C:/Users/varon/OneDrive/Escritorio/investigacion/bases de datos/Pakistan.rds")


df_final <- df_final[!is.na(df_final$url),]
df_final <- cSplit(df_final, splitCols = c("date"), sep = ".", direction = "wide", drop = FALSE)
names(df_final)[5:7] <- c("day","month","year")
df_final <- df_final[,c(1,2,3,4,5,6,7)]

saveRDS(df_final, file = "C:/Users/varon/OneDrive/Escritorio/investigacion/bases de datos/Pakistan.rds")
