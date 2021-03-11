import requests
import threading
from bs4 import BeautifulSoup
import time

def TestFunction():
	return 'Test successful'

def IterateOverItems(dictionaries):
	sales = 0
	for dictionary in dictionaries:
		sales += dictionary['purchaseCount']
	return sales

def IterateOverGroupItems(dictionaries):
	items = {}
	for dictionary in dictionaries:
		items.update({dictionary['id'] : dictionary['purchaseCount']})
	return items

def GetRidOfZeroes(dictionary):
	for group in list(dictionary.keys()):
			for item in list(dictionary[group].keys()):
				if dictionary[group][item] == 0:
					del dictionary[group][item]
	return dictionary

def ReturnSalesOfOwned(groups, itemsales):
	ownedsales = 0
	for group in groups:
		groupid = group[0]
		grouprank = group[1]
		if grouprank == 255:
			for item in list(itemsales[groupid].keys()):
				ownedsales += itemsales[groupid][item]
			del itemsales[groupid]
	return ownedsales, itemsales


def WebscrapePage(link, username, sales):
	try:
		page = requests.get(link)
		soup = BeautifulSoup(page.content, 'html.parser')
		details = soup.find(id = 'item-details')
		name = details.find_all('a', {'class': 'text-name'})[1].text
		if name == username:
			thread = threading.current_thread()
			thread.sales = sales
			print('user created group item!')
			return
		else:
			return
	except:
		print('WEBSCRAPE EXCEPTION')
		return

def GetGroupItemPages(itemsalesdict):
	pages = {}
	for group in list(itemsalesdict.keys()):
		for item in list(itemsalesdict[group].keys()):
			pages['https://www.roblox.com/catalog/' + str(item)] = itemsalesdict[group][item]
	return pages

def GetUsername(userid):
	URL = 'https://api.roblox.com/users/' + str(userid)
	req = requests.get(URL)
	print('got username for', userid)
	data = req.json()
	username = data['Username']
	return username

def PlayerCanEdit(item, userid):
	URL = 'https://api.roblox.com/users/' + str(userid) + '/canmanage/' + str(item)
	req = requests.get(URL)
	print('checked if', userid, 'could manage', item)
	maindata = req.json()
	if maindata['CanManage'] == True:
		return True
	else:
		return False
  
def GetGroupItems(groupid, userid, rank, cursor = None, lastpage = False, iteration = 1): #if player cannot edit, return empty list, else return item and sales in tuple
	thread = threading.current_thread()
	URL = 'https://catalog.roblox.com/v1/search/items/details'
	PARAMS = {'Category' : 1, 'CreatorTargetId' : groupid, 'CreatorType' : 2, 'SortType' : 2}
	if cursor != None:
		PARAMS.update({'Cursor' : cursor})
	req = requests.get(url = URL, params = PARAMS)
	data = req.json()
	if 'data' in data:
		data_body = data['data']
	else:
		print("REQUEST THROTTLED, trying again", data)
		time.sleep(0.5)
		GetGroupItems(groupid, userid, rank, cursor, lastpage, iteration)
		return
	if 'errors' in data.keys():
		print('errored on group', groupid)
		return
	elif len(data_body) == 0:
		print('zero items for group', groupid)
		return
	else:
		nextpage = data['nextPageCursor']
		thread.items[groupid].update(IterateOverGroupItems(data_body))
		if iteration == 10: #cut off large groups
			return
		if lastpage:
			if nextpage != None:
				GetGroupItems(groupid, userid, rank, nextpage, True, iteration + 1)
			return
		elif PlayerCanEdit(list(thread.items[groupid].keys())[0], userid):
			if nextpage != None:
				GetGroupItems(groupid, userid, rank, nextpage, True, iteration + 1)
			return
		else:
			thread.items = {groupid: {}}
			return

def GetGroups(userid, timestried = 0):
	URL = 'https://groups.roblox.com/v2/users/' + str(userid) + '/groups/roles'
	req = requests.get(URL)
	maindata = req.json()
	if (not 'data' in maindata):
		return GetGroups(userid)
	if len(maindata['data']) == 0:
		return []
	groupids = [[dictionary['group']['id'], dictionary['role']['rank']] for dictionary in maindata['data']]
	return groupids

def GetGroupSales(userid):
	sales = 0
	groups = GetGroups(userid)
	if len(groups) == 0:
		return sales
	itemsales = {}
	threads = []
	iterator = 0
	for grouplist in groups:
		group = grouplist[0]
		rank = grouplist[1]
		iterator += 1
		thread = threading.Thread(target = GetGroupItems, args = [group, userid, rank, None])
		thread.items = {group : {}}
		threads.append(thread)
		thread.start()
		if iterator == 1:
			iterator = 0
			for thread in threads:
				thread.join()
				itemsales.update(thread.items)
			threads = []
	for thread in threads:
		thread.join()
		itemsales.update(thread.items)
	threads = []

	print(itemsales)

	itemsales = GetRidOfZeroes(itemsales)
	newsales, itemsales = ReturnSalesOfOwned(groups, itemsales)
	print('NEW SALES ARE', newsales)
	sales += newsales
	pages = GetGroupItemPages(itemsales)
	username = GetUsername(userid)


	iterator = 0 
	for page in list(pages.keys()):
		iterator += 1
		thread = threading.Thread(target = WebscrapePage, args = [page, username, pages[page]])
		thread.sales = 0
		threads.append(thread)
		thread.start()
		if iterator == 1:
			iterator = 0
			for thread in threads:
				thread.join()
				sales += thread.sales
			threads = []
	for thread in threads:
		thread.join()
		sales += thread.sales
	threads = []

	return sales

def GetSoloSales(userid, cursor = None):
	if not type(userid) is int:
		return 'ERROR'
	sales = 0
	URL = 'https://catalog.roblox.com/v1/search/items/details'
	PARAMS = {'Category' : 1, 'CreatorTargetId' : userid}
	if cursor != None:
		PARAMS.update({'Cursor' : cursor})
	req = requests.get(url = URL, params = PARAMS)
	data = req.json()
	data_body = data['data']
	if 'errors' in data.keys():
		print('errored on user', userid)
		return 'ERROR'
	elif len(data_body) == 0:
		print('zero solo sales for', userid)
		return sales
	else:
		nextpage = data['nextPageCursor']
		sales += IterateOverItems(data_body)
		if nextpage != None:
			sales += GetSoloSales(userid, nextpage)
		return sales

def GetTotalSales(userid):
  print('getting total sales')
  solo_sales = GetSoloSales(userid)
  group_sales = GetGroupSales(userid)
  print('final sales are', group_sales + solo_sales)
  current_thread = threading.current_thread()
  if type(solo_sales) is str: #return 0 total sales if solo sales errored
    return
  else:
    if type(group_sales) is str:
      current_thread.sales = solo_sales
      return
    else:
      current_thread.sales = solo_sales + group_sales
      return