#### globals ####

# library -----------------------------------------------------------------

suppressWarnings(
  library(tidyverse)
)

# seed
set.seed(953109)

# custom ggplot theme -----------------------------------------------------

# Create a custom theme
theme_arrows <- function() {
  theme_minimal() +
    theme(
      axis.text = element_blank(),
      axis.title = element_text(hjust = 1, face = "bold"),
      axis.line = element_line(arrow = arrow(length = unit(0.1, "in")))
    ) 
}
