# Samil Power uploader

PVOutput uploader for the following Samil Power inverters: SolarRiver TD
series, SolarRiver TL-D series, SolarLake TL series.

I use it for my system [here](http://pvoutput.org/intraday.jsp?sid=44819).

## Usage

When you run the binary, it retrieves the current generation data from the
inverter(s) and directly uploads this to PVOutput. The system ID and
API key is specified on the command-line, as follows:

    TODO: paste ./solar -h output

You can run the binary every 5 or 15 minutes to upload to PVOutput
periodically.

If your system has multiple network interfaces, it is possible that the wrong
network interface is used. This will result in that the inverter(s) cannot be
found. In that case you can force a certain interface with the `-interface`
option, which you should set to your system's local network IPv4 address.

## Run automatically

### Linux

Cron is the easiest, add the following cron entry (`crontab -e`):

    */5 * * * *  /path/to/solar -system-id 12345 -api-key ASDFASDFASDFASDF

### Windows

Try searching `windows cron alternative`, it seems like `schtasks` can be used
for this. You could try the following command to get more info: `schtasks /?`.

## Multiple inverters

You can specify to get data from multiple inverters via the command-line
arguments. You can also specify filters to match only inverters with a certain
serial number or IP address. When you choose to upload data from multiple
inverters to a single PVOutput system, energy data is accumulated and other
data such as temperature and voltage is averaged.

## More info

I really like getting feedback or ideas, so if anything is unclear or could be
done better or is great, you can make an
[issue](https://github.com/mhvis/solar/issues) or
[contact me](mailto:mail@maartenvisscher.nl) directly.

## Info

The protocol used by these inverters is (somewhat) described
[here](https://github.com/mhvis/solar/wiki/Communication-protocol).
