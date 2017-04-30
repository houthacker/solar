package main

import (
	"flag"
)

var interfaceIP = flag.String("interface", "", "the IP address of the network interface used to bind to (optional)")
var systemID = flag.String("system-id", "", "PVOutput system ID")
var apiKey = flag.String("api-key", "", "PVOutput API key")
var inverterCount = flag.Int("inverters", 1, "number of inverters to fetch data from. If greater than 1, the data of the multiple inverters will be accumulated or averaged depending on type of data")

func main() {
	flag.Parse()
}
